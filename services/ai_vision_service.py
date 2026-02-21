"""
Servico de identificacao de equipamentos via IA Vision.
Arquivo: services/ai_vision_service.py

Provedores suportados:
- Gemini (Flash-Lite) - PRINCIPAL - melhor identificacao de produtos
- Groq (Llama 4 Scout) - FALLBACK - 1.000 req/dia gratis
- Google Custom Search - busca de foto oficial do produto

Este servico eh isolado - nao depende de nenhum model ou route existente.
Chamado apenas pelas rotas /equipment/ai-* em routes/equipment.py
"""
import requests
import base64
import json
import os
from werkzeug.utils import secure_filename


# Categorias exatas do sistema - NAO ALTERAR
CATEGORIAS_VALIDAS = {
    'SOM': 'Som',
    'LUZ': 'Luz',
    'MATERIAIS': 'Materiais',
    'INSTRUMENTOS': 'Instrumentos'
}

# Prompt compartilhado entre provedores
PROMPT_IDENTIFICACAO = """Analise esta imagem de um equipamento de entretenimento/eventos.

Identifique e retorne APENAS um JSON valido (sem markdown, sem ```):

{
    "category": "SOM ou LUZ ou MATERIAIS ou INSTRUMENTOS",
    "type": "tipo especifico (ex: Caixa de Som Ativa, Mesa de Som, Moving Head, Cabo XLR, Guitarra)",
    "brand": "marca do fabricante (ex: JBL, Behringer, Shure, Martin)",
    "model": "modelo especifico (ex: EON715, X32, SM58)",
    "name": "nome completo (ex: Caixa de Som JBL EON715)",
    "image_search": "termo de busca para foto oficial do produto (ex: JBL EON715 official product photo)"
}

Regras:
- category DEVE ser exatamente: SOM, LUZ, MATERIAIS ou INSTRUMENTOS
- SOM = caixas de som, mesas de som, microfones, processadores, amplificadores
- LUZ = PAR LED, moving head, projetores, mesas de luz, refletores
- MATERIAIS = cabos, cases, estantes, tripes, conectores
- INSTRUMENTOS = guitarra, baixo, teclado, bateria, violao
- Se nao conseguir identificar, retorne {"error": "Nao foi possivel identificar o equipamento"}
"""


def _clean_json_response(text):
    """Remove markdown e extrai JSON puro da resposta da IA."""
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    return text


def _validate_category(result):
    """Valida e normaliza a categoria retornada pela IA."""
    if 'category' in result:
        cat_upper = result['category'].upper().strip()
        if cat_upper in CATEGORIAS_VALIDAS:
            result['category'] = CATEGORIAS_VALIDAS[cat_upper]
        else:
            result['category'] = 'Som'  # fallback seguro
    return result


# ============================================
# PROVEDOR GROQ (Llama 4 Scout) - PRINCIPAL
# 1.000 RPD, 30 RPM, Vision nativo
# ============================================

def _identify_groq(image_bytes, api_key):
    """Identifica equipamento usando Groq + Llama 4 Scout."""
    import time

    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    url = 'https://api.groq.com/openai/v1/chat/completions'

    payload = {
        'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': PROMPT_IDENTIFICACAO},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ],
        'temperature': 0.1,
        'max_tokens': 500
    }

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    response = None

    # Ate 3 tentativas com espera crescente
    for attempt in range(3):
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 429:
            wait_time = (attempt + 1) * 5
            print(f"[Groq] Rate limit 429 - tentativa {attempt + 1}/3, aguardando {wait_time}s...")
            time.sleep(wait_time)
            continue
        else:
            break

    if response.status_code != 200:
        error_detail = ''
        try:
            error_detail = response.json().get('error', {}).get('message', response.text[:200])
        except:
            error_detail = response.text[:200]
        print(f"[Groq] Erro {response.status_code}: {error_detail}")
        return {'error': f'Erro Groq: {response.status_code} - {error_detail}'}

    data = response.json()

    # Extrair texto da resposta (formato OpenAI)
    text = data.get('choices', [{}])[0].get('message', {}).get('content', '')

    if not text:
        return {'error': 'Resposta vazia do Groq'}

    text = _clean_json_response(text)
    result = json.loads(text)
    result = _validate_category(result)

    return result


# ============================================
# PROVEDOR GEMINI (Flash-Lite) - FALLBACK
# ~20 RPD, 15 RPM
# ============================================

def _identify_gemini(image_bytes, api_key):
    """Identifica equipamento usando Gemini Vision (fallback)."""
    import time

    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}'

    payload = {
        'contents': [{
            'parts': [
                {'text': PROMPT_IDENTIFICACAO},
                {
                    'inline_data': {
                        'mime_type': 'image/jpeg',
                        'data': image_base64
                    }
                }
            ]
        }]
    }

    headers = {
        'Content-Type': 'application/json'
    }

    response = None

    # Ate 3 tentativas com espera crescente
    for attempt in range(3):
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 429:
            wait_time = (attempt + 1) * 5
            print(f"[Gemini] Rate limit 429 - tentativa {attempt + 1}/3, aguardando {wait_time}s...")
            time.sleep(wait_time)
            continue
        else:
            break

    if response.status_code != 200:
        error_detail = ''
        try:
            error_detail = response.json().get('error', {}).get('message', response.text[:200])
        except:
            error_detail = response.text[:200]
        print(f"[Gemini] Erro {response.status_code}: {error_detail}")
        return {'error': f'Erro Gemini: {response.status_code} - {error_detail}'}

    data = response.json()

    # Extrair texto da resposta (formato Gemini)
    text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

    if not text:
        return {'error': 'Resposta vazia do Gemini'}

    text = _clean_json_response(text)
    result = json.loads(text)
    result = _validate_category(result)

    return result


# ============================================
# FUNCAO PRINCIPAL - ROTEADOR
# ============================================

def identify_equipment(image_bytes, provider='gemini', api_key=None):
    """
    Identifica equipamento via IA Vision.
    Roteia para Gemini (principal) ou Groq (fallback).

    Args:
        image_bytes: bytes da imagem capturada
        provider: 'gemini' ou 'groq'
        api_key: chave API do provedor

    Returns:
        dict com campos: category, type, brand, model, name
        ou dict com campo: error
    """
    # Fallback: tentar variavel de ambiente se nao veio api_key
    if not api_key:
        if provider == 'gemini':
            api_key = os.environ.get('GEMINI_API_KEY', '')
        else:
            api_key = os.environ.get('GROQ_API_KEY', '')

    if not api_key:
        return {'error': f'API Key do {provider.upper()} nao configurada. Configure em Configuracoes > Inteligencia Artificial.'}

    try:
        if provider == 'groq':
            return _identify_groq(image_bytes, api_key)
        elif provider == 'gemini':
            return _identify_gemini(image_bytes, api_key)
        else:
            return {'error': f'Provedor desconhecido: {provider}'}

    except json.JSONDecodeError:
        return {'error': 'Resposta da IA nao eh JSON valido'}
    except requests.exceptions.Timeout:
        return {'error': 'Timeout na comunicacao com IA'}
    except requests.exceptions.ConnectionError:
        return {'error': 'Erro de conexao com IA'}
    except Exception as e:
        return {'error': f'Erro inesperado: {str(e)}'}


# ============================================
# BUSCA DE FOTO OFICIAL - Via Gemini (sem CSE)
# Usa a mesma API Key do Gemini Vision
# ============================================

def search_product_image(brand, model, api_key=None, cse_cx=None):
    """
    Busca foto oficial do produto.
    Estrategia:
    1. Se CSE configurado, usa Google Custom Search (100/dia gratis)
    2. Senao, pede ao Gemini uma URL de imagem oficial

    Args:
        brand: marca do equipamento (ex: JBL)
        model: modelo do equipamento (ex: EON715)
        api_key: Google/Gemini API Key
        cse_cx: Google Custom Search Engine ID (opcional)

    Returns:
        string com path local (ex: /static/uploads/models/JBL_EON715_official.jpg)
        ou None se falhar
    """
    # Fallback para variaveis de ambiente
    if not api_key:
        api_key = os.environ.get('GEMINI_API_KEY', '') or os.environ.get('GOOGLE_API_KEY', '')
    if not cse_cx:
        cse_cx = os.environ.get('GOOGLE_CSE_CX', '')

    if not api_key or not brand or not model:
        print(f"[ImageSearch] Faltando: api_key={bool(api_key)}, brand={brand}, model={model}")
        return None

    # Estrategia 1: Google Custom Search (se CSE configurado)
    if cse_cx:
        result = _search_via_cse(brand, model, api_key, cse_cx)
        if result:
            return result
        print(f"[ImageSearch] CSE nao retornou resultado, tentando via Gemini...")

    # Estrategia 2: Pedir ao Gemini uma URL de imagem
    return _search_via_gemini(brand, model, api_key)


def _search_via_cse(brand, model, api_key, cse_cx):
    """Busca imagem via Google Custom Search API."""
    try:
        search_query = f"{brand} {model} product photo"
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': api_key,
            'cx': cse_cx,
            'q': search_query,
            'searchType': 'image',
            'num': 1,
            'imgSize': 'large',
            'safe': 'active'
        }

        print(f"[ImageSearch/CSE] Buscando: {search_query}")
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            error_detail = ''
            try:
                error_detail = response.json().get('error', {}).get('message', '')
            except:
                error_detail = response.text[:200]
            print(f"[ImageSearch/CSE] Erro {response.status_code}: {error_detail}")
            return None

        data = response.json()
        items = data.get('items', [])

        if not items:
            print(f"[ImageSearch/CSE] Nenhuma imagem encontrada")
            return None

        image_url = items[0].get('link', '')
        if not image_url:
            return None

        return _download_and_save_image(image_url, brand, model, 'cse')

    except Exception as e:
        print(f"[ImageSearch/CSE] Erro: {str(e)}")
        return None


def _search_via_gemini(brand, model, api_key):
    """Pede ao Gemini uma URL de imagem oficial do produto."""
    try:
        import time

        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}'

        prompt = f"""Preciso da URL de uma imagem oficial do produto {brand} {model} (equipamento de audio/iluminacao/entretenimento).

Retorne APENAS um JSON valido (sem markdown, sem ```):
{{"image_url": "URL_DIRETA_DA_IMAGEM.jpg"}}

Regras:
- A URL deve ser de uma imagem REAL e ACESSIVEL (terminando em .jpg, .png, .webp)
- Prefira sites oficiais do fabricante: jbl.com, behringer.com, shure.com, harman.com
- Ou Amazon, B&H Photo, Thomann, MusicStore
- NAO invente URLs. Se nao souber uma URL real, retorne {{"image_url": null}}
- A imagem deve mostrar o produto em fundo branco ou neutro (foto produto)
"""

        payload = {
            'contents': [{
                'parts': [{'text': prompt}]
            }]
        }

        headers = {
            'Content-Type': 'application/json'
        }

        # Retry para 429
        response = None
        for attempt in range(3):
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 429:
                wait_time = (attempt + 1) * 5
                print(f"[ImageSearch/Gemini] Rate limit 429 - tentativa {attempt + 1}/3, aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                break

        if response.status_code != 200:
            print(f"[ImageSearch/Gemini] Erro {response.status_code}")
            return None

        data = response.json()
        text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

        # Limpar markdown
        text = _clean_json_response(text)
        result = json.loads(text)
        image_url = result.get('image_url')

        if not image_url:
            print(f"[ImageSearch/Gemini] Gemini nao encontrou URL para {brand} {model}")
            return None

        print(f"[ImageSearch/Gemini] URL sugerida: {image_url}")
        return _download_and_save_image(image_url, brand, model, 'gemini')

    except Exception as e:
        print(f"[ImageSearch/Gemini] Erro: {str(e)}")
        return None


def _download_and_save_image(image_url, brand, model, source='unknown'):
    """Baixa imagem da URL e salva localmente."""
    try:
        img_response = requests.get(image_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; TourManager/1.0)'
        })

        if img_response.status_code != 200:
            print(f"[ImageSearch/{source}] Erro ao baixar imagem: {img_response.status_code}")
            return None

        # Verificar se eh realmente uma imagem
        content_type = img_response.headers.get('Content-Type', '')
        if 'image' not in content_type:
            print(f"[ImageSearch/{source}] Conteudo nao eh imagem: {content_type}")
            return None

        # Verificar tamanho minimo (evitar placeholders/1x1 pixels)
        if len(img_response.content) < 5000:
            print(f"[ImageSearch/{source}] Imagem muito pequena ({len(img_response.content)} bytes), ignorando")
            return None

        # Determinar extensao
        if 'png' in content_type:
            ext = 'png'
        elif 'webp' in content_type:
            ext = 'webp'
        else:
            ext = 'jpg'

        # Salvar em static/uploads/models/ (mesmo padrao do projeto)
        safe_brand = brand.upper().replace(' ', '_')
        safe_model = model.upper().replace(' ', '_')
        filename = secure_filename(f"{safe_brand}_{safe_model}_official.{ext}")
        upload_folder = os.path.join('static', 'uploads', 'models')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)

        with open(filepath, 'wb') as f:
            f.write(img_response.content)

        local_path = f"/{filepath}"
        print(f"[ImageSearch/{source}] Salva em: {local_path}")
        return local_path

    except Exception as e:
        print(f"[ImageSearch/{source}] Erro download: {str(e)}")
        return None


# ============================================
# FUNCAO DE TESTE DE CONEXAO
# ============================================

def test_ai_connection(provider='groq', api_key=None):
    """
    Testa conexao com o provedor de IA.

    Returns:
        dict com success, message, provider
    """
    if not api_key:
        return {'success': False, 'error': 'API Key nao informada'}

    try:
        if provider == 'groq':
            url = 'https://api.groq.com/openai/v1/models'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                models = response.json().get('data', [])
                model_names = [m.get('id', '') for m in models[:5]]
                return {
                    'success': True,
                    'message': f'Conexao OK! {len(models)} modelos disponiveis.',
                    'provider': 'Groq (Llama 4 Scout)',
                    'models': model_names
                }
            else:
                error = response.json().get('error', {}).get('message', 'Erro desconhecido')
                return {'success': False, 'error': f'Erro Groq: {error}'}

        elif provider == 'gemini':
            url = f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}'
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                models = response.json().get('models', [])
                return {
                    'success': True,
                    'message': f'Conexao OK! {len(models)} modelos disponiveis.',
                    'provider': 'Google Gemini'
                }
            else:
                error_detail = ''
                try:
                    error_detail = response.json().get('error', {}).get('message', '')
                except:
                    error_detail = response.text[:200]
                return {'success': False, 'error': f'Erro Gemini: {error_detail}'}

        else:
            return {'success': False, 'error': f'Provedor desconhecido: {provider}'}

    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Timeout na conexao'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Erro de conexao'}
    except Exception as e:
        return {'success': False, 'error': f'Erro: {str(e)}'}