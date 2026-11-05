import enum


class AuthProvider(enum.StrEnum):
    LOCAL = "local"
    GOOGLE = "google"
    FACEBOOK = "facebook"


class LeadStage(enum.StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    FOLLOW_UP = "follow_up"
    QUALIFIED = "qualified"
    ORDER_CONFIRMED = "order_confirmed"
    LOST = "lost"


class OrderStatus(enum.StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentMethod(enum.StrEnum):
    COD = "cod"
    PREPAID = "prepaid"
