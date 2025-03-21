from rest_framework.routers import DefaultRouter

from hope_payment_gateway.api.fsp import views
from hope_payment_gateway.api.western_union import views as wu_views

app_name = "api"

router = DefaultRouter()

router.register(
    r"account_types",
    views.AccountTypeViewSet,
    basename="account_type",
)
router.register(
    r"delivery_mechanisms",
    views.DeliveryMechanismViewSet,
    basename="delivery_mechanism",
)
router.register(r"fsp", views.FinancialServiceProviderViewSet, basename="fsp")
router.register(
    r"payment_instructions",
    views.PaymentInstructionViewSet,
    basename="payment-instruction",
)
router.register(r"payment_records", views.PaymentRecordViewSet, basename="payment-record")
router.register(r"export_templates", views.ExportTemplateViewSet, basename="export-template")
router.register(r"config", views.ConfigurationViewSet, basename="config")

router.register(r"wu/corridors", wu_views.CorridorViewSet, basename="wu-corridor")
router.register(
    r"wu/provider_code",
    wu_views.ServiceProviderCodeViewSet,
    basename="wu-service-provider-code",
)

router.register(r"wu/files", wu_views.FileViewset, basename="wu-files")

urlpatterns = router.urls
