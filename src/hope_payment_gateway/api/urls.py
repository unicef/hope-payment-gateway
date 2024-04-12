from rest_framework.routers import DefaultRouter

from hope_payment_gateway.api.fsp import views
from hope_payment_gateway.api.western_union import views as wu_views

app_name = "api"

router = DefaultRouter()

router.register(r"fsp", views.FinancialServiceProviderViewSet, basename="fsp")
router.register(r"payment_instructions", views.PaymentInstructionViewSet, basename="payment-instruction")
router.register(r"payment_records", views.PaymentRecordViewSet, basename="payment-record")
router.register(r"config", views.ConfigurationViewSet, basename="config")

router.register(r"wu/corridors", wu_views.CorridorViewSet, basename="corridors")


urlpatterns = router.urls
