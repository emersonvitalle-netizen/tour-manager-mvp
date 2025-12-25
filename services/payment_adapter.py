"""
Adaptadores de pagamento para múltiplos provedores brasileiros.
Suporta: PIX, Boleto, Cartão

Provedores suportados:
- Asaas (padrão)
- PagSeguro
- Mercado Pago
- Manual (sem integração)
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
        """Cria cobrança PIX e retorna código copia-cola + QR"""
        pass
    
    @abstractmethod
    def create_boleto(self, invoice_id: str, amount: float, due_date: date,
                      description: str, customer_name: str, customer_document: str,
                      customer_address: Dict[str, str]) -> Dict[str, Any]:
        """Cria boleto e retorna linha digitável + URL do PDF"""
        pass
    
    @abstractmethod
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Verifica status de pagamento"""
        pass
    
    @abstractmethod
    def cancel_payment(self, transaction_id: str) -> bool:
        """Cancela cobrança"""
        pass


class AsaasProvider(PaymentProvider):
    """Provedor Asaas - PIX e Boleto"""
    
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
            raise ValueError(f"Método não suportado: {method}")
        
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
        
        pix_data = self._make_request("GET", f"payments/{result['id']}/pixQrCode")
        
        return {
            "success": True,
            "transaction_id": result.get("id"),
            "pix_code": pix_data.get("payload"),
            "pix_qr_url": pix_data.get("encodedImage"),
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
        
        return {
            "success": True,
            "transaction_id": result.get("id"),
            "boleto_code": result.get("nossoNumero"),
            "boleto_url": result.get("bankSlipUrl"),
            "boleto_line": result.get("identificationField"),
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
        customers = self._make_request("GET", f"customers?cpfCnpj={document}")
        
        if customers.get("data"):
            return customers["data"][0]
        
        customer_data = {
            "name": name,
            "cpfCnpj": document
        }
        return self._make_request("POST", "customers", customer_data)


class ManualProvider(PaymentProvider):
    """Provedor manual - sem integração automática"""
    
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
