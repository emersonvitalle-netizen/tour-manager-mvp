"""
Adaptadores de Nota Fiscal de Serviço (NFSe) para múltiplos provedores.

Provedores suportados:
- Focus NFe
- Enotas
- NFE.io
- Manual (sem integração)
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
import json


class NFSeProvider(ABC):
    """Interface base para provedores de NFSe"""
    
    @abstractmethod
    def emit_nfse(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Emite NFSe e retorna número + URL"""
        pass
    
    @abstractmethod
    def cancel_nfse(self, nfse_id: str, reason: str) -> Dict[str, Any]:
        """Cancela NFSe emitida"""
        pass
    
    @abstractmethod
    def get_nfse_status(self, nfse_id: str) -> Dict[str, Any]:
        """Consulta status da NFSe"""
        pass
    
    @abstractmethod
    def get_nfse_pdf(self, nfse_id: str) -> str:
        """Retorna URL do PDF da NFSe"""
        pass


class FocusNFeProvider(NFSeProvider):
    """Provedor Focus NFe"""
    
    def __init__(self, api_key: str, environment: str = "production"):
        self.api_key = api_key
        self.environment = environment
        self.base_url = f"https://api.focusnfe.com.br/v2"
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        import requests
        from base64 import b64encode
        
        auth = b64encode(f"{self.api_key}:".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=data)
        else:
            raise ValueError(f"Método não suportado: {method}")
        
        return response.json()
    
    def emit_nfse(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        invoice_data deve conter:
        - company_cnpj: CNPJ do emitente
        - client_document: CPF/CNPJ do cliente
        - client_name: Nome do cliente
        - service_code: Código do serviço municipal
        - description: Descrição do serviço
        - value: Valor total
        - iss_percent: Alíquota ISS
        """
        nfse_data = {
            "data_emissao": datetime.now().isoformat(),
            "prestador": {
                "cnpj": invoice_data.get("company_cnpj")
            },
            "tomador": {
                "cpf_cnpj": invoice_data.get("client_document"),
                "razao_social": invoice_data.get("client_name"),
                "email": invoice_data.get("client_email")
            },
            "servico": {
                "codigo_tributacao_municipio": invoice_data.get("service_code", ""),
                "discriminacao": invoice_data.get("description"),
                "valor_servicos": invoice_data.get("value"),
                "aliquota_iss": invoice_data.get("iss_percent", 5.0)
            }
        }
        
        ref = f"nfse-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result = self._make_request("POST", f"nfse?ref={ref}", nfse_data)
        
        return {
            "success": result.get("status") not in ["erro", "rejeitada"],
            "nfse_id": ref,
            "nfse_number": result.get("numero"),
            "nfse_code": result.get("codigo_verificacao"),
            "nfse_url": result.get("url"),
            "provider": "focus_nfe",
            "raw_response": json.dumps(result)
        }
    
    def cancel_nfse(self, nfse_id: str, reason: str) -> Dict[str, Any]:
        result = self._make_request("DELETE", f"nfse/{nfse_id}", {"justificativa": reason})
        return {
            "success": result.get("status") == "cancelado",
            "raw_response": json.dumps(result)
        }
    
    def get_nfse_status(self, nfse_id: str) -> Dict[str, Any]:
        result = self._make_request("GET", f"nfse/{nfse_id}")
        
        status_map = {
            "processando": "processing",
            "autorizado": "authorized",
            "erro": "error",
            "cancelado": "cancelled"
        }
        
        return {
            "status": status_map.get(result.get("status"), "unknown"),
            "raw_response": json.dumps(result)
        }
    
    def get_nfse_pdf(self, nfse_id: str) -> str:
        result = self._make_request("GET", f"nfse/{nfse_id}")
        return result.get("url", "")


class ManualNFSeProvider(NFSeProvider):
    """Provedor manual - sem integração automática"""
    
    def emit_nfse(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "nfse_id": f"MANUAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "nfse_number": None,
            "nfse_code": None,
            "nfse_url": None,
            "provider": "manual",
            "message": "Emita a NFSe manualmente no portal da prefeitura"
        }
    
    def cancel_nfse(self, nfse_id: str, reason: str) -> Dict[str, Any]:
        return {"success": True, "message": "Cancele manualmente"}
    
    def get_nfse_status(self, nfse_id: str) -> Dict[str, Any]:
        return {"status": "manual", "message": "Verifique manualmente"}
    
    def get_nfse_pdf(self, nfse_id: str) -> str:
        return ""


def get_nfse_provider(provider_name: str = "manual", **config) -> NFSeProvider:
    """Factory para obter o provedor de NFSe configurado"""
    providers = {
        "focus_nfe": lambda: FocusNFeProvider(
            api_key=config.get("api_key", ""),
            environment=config.get("environment", "production")
        ),
        "manual": lambda: ManualNFSeProvider()
    }
    
    factory = providers.get(provider_name, providers["manual"])
    return factory()
