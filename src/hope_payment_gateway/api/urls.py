from rest_framework.routers import DefaultRouter

from hope_payment_gateway.api.fsp import views

app_name = "api"

router = DefaultRouter()

router.register(r"fsp", views.FinancialServiceProviderViewSet, basename="fsp")
router.register(r"payment_instructions", views.PaymentInstructionViewSet, basename="payment-instruction")
router.register(r"payment_records", views.PaymentRecordViewSet, basename="payment-record")

urlpatterns = router.urls
