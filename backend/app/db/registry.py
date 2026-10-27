"""Importa TODOS los modelos para que queden registrados en Base.metadata
(necesario para create_all, Alembic y para resolver relaciones declaradas por nombre)."""

from app.db.base import Base
from app.modules.billing.models import BillingNotification, BillingPayment, Subscription
from app.modules.products.models import Product, ProductCategory
from app.modules.privacy.models import PrivacyConsent
from app.modules.orders.models import StoreOrder, StoreOrderItem
from app.modules.support.models import SellerAdminMessage, SellerAdminReply
from app.modules.stores.models import Store
from app.modules.users.models import User

__all__ = ["Base", "BillingNotification", "BillingPayment", "PrivacyConsent", "SellerAdminMessage", "SellerAdminReply", "StoreOrder", "StoreOrderItem", "Product", "ProductCategory", "Store", "Subscription", "User"]
