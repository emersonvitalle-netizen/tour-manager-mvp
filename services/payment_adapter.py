"""
Adaptadores de pagamento para multiplos provedores brasileiros.
Suporta: PIX, Boleto, Cartao, NFSe

Provedores suportados:
- Asaas (padrao)
- Manual (sem integracao)
"""
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Dict, Any, Optional
import json


class PaymentProvider(ABC):
    """Interface base para provedores de pagamento"""

    @abstractmethod
    def create_pix(self, invoice_id: str, amount: float, description: str, 
                   customer_name: str, customer_document: str) -> Dict[str, Any]:
        """Cria cobranca PIX e retorna codigo copia-cola + QR"""
        pass

    @abstractmethod
    def create_boleto(self, invoice_id: str, amount: float, due_date: date,
                      description: str, customer_name: str, customer_document: str,
                      customer_address: Dict[str, str]) -> Dict[str, Any]:
        """Cria boleto e retorna linha digitavel + URL do PDF"""
        pass

    @abstractmethod
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Verifica status de pagamento"""
        pass

    @abstractmethod
    def cancel_payment(self, transaction_id: str) -> bool:
        """Cancela cobranca"""
        pass

    @abstractmethod
    def emit_nfse(self, payment_id: str, service_description: str, 
                  service_code: str, value: float, taxes: Dict[str, float]) -> Dict[str, Any]:
        """Emite NFSe vinculada a uma cobranca"""
        pass

    @abstractmethod
    def get_nfse_status(self, nfse_id: str) -> Dict[str, Any]:
        """Consulta status da NFSe"""
        pass

    @abstractmethod
    def get_municipal_services(self) -> Dict[str, Any]:
        """Lista servicos municipais disponiveis"""
        pass


class AsaasProvider(PaymentProvider):
    """Provedor Asaas - PIX, Boleto e NFSe"""

    def __init__(self, api_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.base_url = "https://sandbox.asaas.com/api/v3" if sandbox else "https://www.asaas.com/api/v3"

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        import requests
        headers = {
            "access_token": self.api_key,
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Metodo nao suportado: {method}")

        return response.json()

    def create_pix(self, invoice_id: str, amount: float, description: str,
                   customer_name: str, customer_document: str) -> Dict[str, Any]:
        customer = self._get_or_create_customer(customer_name, customer_document)

        payment_data = {
            "customer": customer["id"],
            "billingType": "PIX",
            "value": amount,
            "dueDate": date.today().isoformat(),
            "description": description,
            "externalReference": invoice_id
        }

        result = self._make_request("POST", "payments", payment_data)

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao criar PIX"),
                "provider": "asaas"
            }

        pix_data = self._make_request("GET", f"payments/{result['id']}/pixQrCode")

        return {
            "success": True,
            "transaction_id": result.get("id"),
            "pix_code": pix_data.get("payload"),
            "pix_qr_url": pix_data.get("encodedImage"),
            "invoice_url": result.get("invoiceUrl"),
            "provider": "asaas",
            "raw_response": json.dumps(result)
        }

    def create_boleto(self, invoice_id: str, amount: float, due_date: date,
                      description: str, customer_name: str, customer_document: str,
                      customer_address: Dict[str, str]) -> Dict[str, Any]:
        customer = self._get_or_create_customer(customer_name, customer_document)

        payment_data = {
            "customer": customer["id"],
            "billingType": "BOLETO",
            "value": amount,
            "dueDate": due_date.isoformat(),
            "description": description,
            "externalReference": invoice_id
        }

        result = self._make_request("POST", "payments", payment_data)

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao criar boleto"),
                "provider": "asaas"
            }

        return {
            "success": True,
            "transaction_id": result.get("id"),
            "boleto_code": result.get("nossoNumero"),
            "boleto_url": result.get("bankSlipUrl"),
            "boleto_line": result.get("identificationField"),
            "invoice_url": result.get("invoiceUrl"),
            "provider": "asaas",
            "raw_response": json.dumps(result)
        }

    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        result = self._make_request("GET", f"payments/{transaction_id}")

        status_map = {
            "PENDING": "pending",
            "RECEIVED": "confirmed",
            "CONFIRMED": "confirmed",
            "OVERDUE": "pending",
            "REFUNDED": "refunded",
            "REFUND_REQUESTED": "pending",
            "CHARGEBACK_REQUESTED": "pending",
            "CHARGEBACK_DISPUTE": "pending",
            "AWAITING_CHARGEBACK_REVERSAL": "pending"
        }

        return {
            "status": status_map.get(result.get("status"), "pending"),
            "paid_at": result.get("paymentDate"),
            "raw_response": json.dumps(result)
        }

    def cancel_payment(self, transaction_id: str) -> bool:
        result = self._make_request("DELETE", f"payments/{transaction_id}")
        return result.get("deleted", False)

    def _get_or_create_customer(self, name: str, document: str) -> Dict:
        """Busca ou cria cliente no Asaas"""
        # Limpa documento (remove pontos, tracos)
        clean_doc = ''.join(filter(str.isdigit, document)) if document else ''

        if clean_doc:
            customers = self._make_request("GET", f"customers?cpfCnpj={clean_doc}")
            if customers.get("data"):
                return customers["data"][0]

        customer_data = {
            "name": name,
            "cpfCnpj": clean_doc or None
        }
        return self._make_request("POST", "customers", customer_data)

    # ============================================
    # METODOS NFSe
    # ============================================

    def get_municipal_services(self, description_filter: str = None) -> Dict[str, Any]:
        """Lista servicos municipais disponiveis para NFSe"""
        endpoint = "invoices/municipalServices"
        if description_filter:
            endpoint += f"?description={description_filter}"

        result = self._make_request("GET", endpoint)

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao listar servicos"),
                "services": []
            }

        return {
            "success": True,
            "services": result.get("data", []),
            "total": result.get("totalCount", 0)
        }

    def emit_nfse(self, payment_id: str = None, customer_id: str = None,
                  service_description: str = "", service_code: str = None,
                  service_id: str = None, service_name: str = None,
                  value: float = 0, effective_date: str = None,
                  taxes: Dict[str, float] = None, observations: str = None) -> Dict[str, Any]:
        """
        Emite NFSe via Asaas

        Args:
            payment_id: ID da cobranca no Asaas (para NFSe vinculada)
            customer_id: ID do cliente no Asaas (para NFSe avulsa)
            service_description: Descricao do servico
            service_code: Codigo do servico municipal (municipalServiceCode)
            service_id: ID do servico municipal (municipalServiceId)
            service_name: Nome do servico municipal
            value: Valor da NFSe
            effective_date: Data de competencia (YYYY-MM-DD)
            taxes: Dicionario com aliquotas {iss, cofins, csll, inss, ir, pis}
            observations: Observacoes adicionais
        """
        nfse_data = {
            "serviceDescription": service_description,
            "value": value,
            "effectiveDate": effective_date or date.today().isoformat()
        }

        # Vincula a cobranca existente OU cliente (avulsa)
        if payment_id:
            nfse_data["payment"] = payment_id
        elif customer_id:
            nfse_data["customer"] = customer_id

        # Servico municipal
        if service_id:
            nfse_data["municipalServiceId"] = service_id
        if service_code:
            nfse_data["municipalServiceCode"] = service_code
        if service_name:
            nfse_data["municipalServiceName"] = service_name

        # Observacoes
        if observations:
            nfse_data["observations"] = observations

        # Impostos
        if taxes:
            nfse_data["taxes"] = {
                "retainIss": taxes.get("retain_iss", False),
                "iss": taxes.get("iss", 0),
                "cofins": taxes.get("cofins", 0),
                "csll": taxes.get("csll", 0),
                "inss": taxes.get("inss", 0),
                "ir": taxes.get("ir", 0),
                "pis": taxes.get("pis", 0)
            }

        result = self._make_request("POST", "invoices", nfse_data)

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao emitir NFSe"),
                "provider": "asaas"
            }

        return {
            "success": True,
            "nfse_id": result.get("id"),
            "nfse_number": result.get("number"),
            "nfse_status": result.get("status"),
            "nfse_url": result.get("pdfUrl"),
            "nfse_xml_url": result.get("xmlUrl"),
            "provider": "asaas",
            "raw_response": json.dumps(result)
        }

    def get_nfse_status(self, nfse_id: str) -> Dict[str, Any]:
        """Consulta status da NFSe"""
        result = self._make_request("GET", f"invoices/{nfse_id}")

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao consultar NFSe")
            }

        status_map = {
            "SCHEDULED": "agendada",
            "PROCESSING": "processando",
            "AUTHORIZED": "autorizada",
            "CANCELED": "cancelada",
            "ERROR": "erro"
        }

        return {
            "success": True,
            "nfse_id": result.get("id"),
            "nfse_number": result.get("number"),
            "status": status_map.get(result.get("status"), result.get("status")),
            "status_raw": result.get("status"),
            "nfse_url": result.get("pdfUrl"),
            "nfse_xml_url": result.get("xmlUrl"),
            "error_message": result.get("errorMessage"),
            "raw_response": json.dumps(result)
        }

    def cancel_nfse(self, nfse_id: str) -> Dict[str, Any]:
        """Cancela NFSe"""
        result = self._make_request("DELETE", f"invoices/{nfse_id}")

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao cancelar NFSe")
            }

        return {
            "success": True,
            "message": "NFSe cancelada com sucesso"
        }

    def authorize_nfse(self, nfse_id: str) -> Dict[str, Any]:
        """Autoriza/emite NFSe agendada imediatamente"""
        result = self._make_request("POST", f"invoices/{nfse_id}/authorize", {})

        if "errors" in result:
            return {
                "success": False,
                "error": result["errors"][0].get("description", "Erro ao autorizar NFSe")
            }

        return {
            "success": True,
            "nfse_id": result.get("id"),
            "status": result.get("status")
        }


class ManualProvider(PaymentProvider):
    """Provedor manual - sem integracao automatica"""

    def create_pix(self, invoice_id: str, amount: float, description: str,
                   customer_name: str, customer_document: str) -> Dict[str, Any]:
        return {
            "success": True,
            "transaction_id": f"MANUAL-PIX-{invoice_id}",
            "pix_code": None,
            "pix_qr_url": None,
            "provider": "manual",
            "message": "Registre o PIX manualmente"
        }

    def create_boleto(self, invoice_id: str, amount: float, due_date: date,
                      description: str, customer_name: str, customer_document: str,
                      customer_address: Dict[str, str]) -> Dict[str, Any]:
        return {
            "success": True,
            "transaction_id": f"MANUAL-BOLETO-{invoice_id}",
            "boleto_code": None,
            "boleto_url": None,
            "provider": "manual",
            "message": "Emita o boleto manualmente"
        }

    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        return {"status": "pending", "message": "Confirme manualmente"}

    def cancel_payment(self, transaction_id: str) -> bool:
        return True

    def emit_nfse(self, payment_id: str = None, customer_id: str = None,
                  service_description: str = "", service_code: str = None,
                  service_id: str = None, service_name: str = None,
                  value: float = 0, effective_date: str = None,
                  taxes: Dict[str, float] = None, observations: str = None) -> Dict[str, Any]:
        return {
            "success": True,
            "nfse_id": f"MANUAL-NFSE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "nfse_number": None,
            "provider": "manual",
            "message": "Emita a NFSe manualmente no portal da prefeitura"
        }

    def get_nfse_status(self, nfse_id: str) -> Dict[str, Any]:
        return {"status": "manual", "message": "Verifique manualmente"}

    def get_municipal_services(self, description_filter: str = None) -> Dict[str, Any]:
        return {"success": True, "services": [], "message": "Configure manualmente"}


def get_payment_provider(provider_name: str = "manual", **config) -> PaymentProvider:
    """Factory para obter o provedor de pagamento configurado"""
    providers = {
        "asaas": lambda: AsaasProvider(
            api_key=config.get("api_key", ""),
            sandbox=config.get("sandbox", True)
        ),
        "manual": lambda: ManualProvider()
    }

    factory = providers.get(provider_name, providers["manual"])
    return factory()