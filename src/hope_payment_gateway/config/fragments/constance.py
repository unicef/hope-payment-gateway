from hope_payment_gateway.config.settings import CACHE_URL

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

CONSTANCE_CONFIG = {
    "MONEYGRAM_THREASHOLD": (
        10000,
        "Hourly threshold of calls to be made to MoneyGram API",
        int,
    ),
    "MONEYGRAM_VENDOR_NUMBER": ("", "MoneyGram Vendor Number", str),
    "MONEYGRAM_SIGNATURE_VERIFICATION_ENABLED": (
        True,
        "MoneyGram: Signature Verification Enabled",
        bool,
    ),
    "PALPAY_VENDOR_NUMBER": ("", "PalPay Vendor Number", str),
    "WESTERN_UNION_THREASHOLD": (
        10000,
        "Hourly threshold of calls to be made to Western Union API",
        int,
    ),
    "WESTERN_UNION_ERRORS": (
        "E0604;T2337;T3251;T3252;T3253;E0801;E1300;R5643;T0305;T0354;T0355;T0357;T0358;T0361;T0365;T0367;T0400;T0402;"
        "T0403;T0410;T0411;T0436;T0440;T0441;T0442;T0445;T0457;T0460;T0462;T0463;T0464;T0466;T0479;T0485;T0488;T0499;"
        "T0780;T0851;T0908;T0998;T1236;T1403;T1404;T1406;T3503;T4443;T4445;T4704;T4816;T4820;T4830;T4832;T4836;T4839;"
        "T4840;T4900;T4977;T4989;T4989;T5499;T5500;T5519;T5522;T6216;T6332;T6750;T6791;T8004;T8881;T9103;T9133;T9980;"
        "U0004;U0006;U0007;U0119;U2400;U2402;U2520;U2521;U2535;U2539;U2540;U7777;U8001;U8004;U8010;U8011;U8100;U8101;"
        "U8200;U8201;U9001;U9002;U9010;U9011;U9013;U9015;U9016;U9020;U9021;U9022;U9023;U9024;U9025;U9081;M0006;T6253;"
        "NONE;E9248;T0371;T8002;T5499;U0051;T5552;E9256",
        "Error codes which depend on WU",
        str,
    ),
    "WESTERN_UNION_DAS_IDENTIFIER": ("", "Identifier", str),  # todo remove
    "WESTERN_UNION_DAS_COUNTER": ("", "Counter", str),  # todo remove
    "WESTERN_UNION_WHITELISTED_ENV": ("uat", "Western Union Env", str),
    "WESTERN_UNION_VENDOR_NUMBER": ("", "Western Union Vendor Number", str),
    "WHITELISTED_IPS": ("127.0.0.1", "IPs", str),
    "WHITELIST_ENABLED": (True, "Whitelist Enabled", bool),
}
CONSTANCE_REDIS_CONNECTION = CACHE_URL
