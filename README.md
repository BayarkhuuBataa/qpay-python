<h1 align="center">
  QPay Python
</h1>

<p align="center">
  <a href="https://github.com/khasbilegt/qpay-python/">
    <img src="https://img.shields.io/github/actions/workflow/status/khasbilegt/qpay-python/qa.yml?label=CI&logo=github&style=for-the-badge" alt="ci status">
  </a>
  <a href="https://codecov.io/github/khasbilegt/qpay-python">
    <img src="https://img.shields.io/codecov/c/github/khasbilegt/qpay-python?logo=codecov&style=for-the-badge" alt="codecov">
  </a>
  <br>
  <a href="https://pypi.org/project/qpay-python/">
    <img src="https://img.shields.io/pypi/v/qpay-python?style=for-the-badge" alt="pypi link">
  </a>
  <a>
    <img src="https://img.shields.io/pypi/pyversions/qpay-python?logo=python&style=for-the-badge" alt="supported python versions">
  </a>
</p>

<p align="center">
  <a href="#usage">Ашиглах</a> •
  <a href="#contribution">Хөгжүүлэлтэнд оролцох</a> •
  <a href="#license">Лиценз</a>
</p>

<p align="center">QPay v2 гүйлгээний сервисүүдийг Python хэлний орчинд ашиглахад зориулсан сан</p>

### <a id="usage"></a>QPayClient -г ашиглах

Хамгийн эхлээд `QPayClient` -с объект үүсгэж авна. Ингэхийн тулд KKTТ ХХК -тай гэрээ хийн нэр, нууц үг авсан байх шаардлагатай. Нэг л удаа үүсгээд авчихсан байхад токен дуусах, сунгах зэрэг дээр санаа зовох шаардлагагүй.

```py
import qpay import QPayClient

client = QPayClient.instance(host="https://merchant.qpay.mn/v2/", username="MERCHANT_USERNAME", password="MERCHANT_PASSWORD")

...
```

QPayClient нь singleton paradigm -г ашигладаг учир нэг л объект үүсгэж, тэрийгээ дахин ашиглана. Шаардлагатай сервисүүдийг үүсгэсэн объектоороо дамжуулан дуудна.

```py
...

payload = {"invoice_code": ... }
invoice = client.invoice_create(json=payload)
print(invoice.qr_text) # 0002010102121531279404962794049600000000KKTQ...

...
```

### Олон worker-т ашиглах

`QPayClient`/`QPayAuth` нь токеныг санах ойд (`InMemoryTokenStore`) хадгалдаг тул нэг процесс дотор л хуваалцана. Хэрэв та олон worker процесстой орчинд ажиллуулж байгаа бол worker бүр өөрийн токен тусад нь татаж авах болно. Үүнээс сэргийлж, `qpay.TokenStore`-г удамшуулан өөрийн (жишээ нь Redis-д тулгуурласан) хувилбараа `token_store` аргументаар дамжуулж болно:

```py
import redis
from qpay import AccessToken, QPayClient, RefreshToken, TokenStore

class RedisTokenStore(TokenStore):
    def __init__(self, client: redis.Redis, key_prefix: str = "qpay"):
        self._client = client
        self._prefix = key_prefix

    def get(self):
        access = self._client.get(f"{self._prefix}:access")
        refresh = self._client.get(f"{self._prefix}:refresh")
        return (
            AccessToken.model_validate_json(access) if access else None,
            RefreshToken.model_validate_json(refresh) if refresh else None,
        )

    def set(self, access_token, refresh_token):
        self._client.set(f"{self._prefix}:access", access_token.model_dump_json())
        self._client.set(f"{self._prefix}:refresh", refresh_token.model_dump_json())

    def lock(self):
        return self._client.lock(f"{self._prefix}:lock", timeout=10)

client = QPayClient.instance(
    host="https://merchant.qpay.mn/v2/",
    username="MERCHANT_USERNAME",
    password="MERCHANT_PASSWORD",
    token_store=RedisTokenStore(redis.Redis()),
)
```

Ингэснээр бүх worker нэг л токен хуваалцах бөгөөд хугацаа дуусах, сэргээх зэргийг нэг л газар зохицуулна.

## <a id="contribution"></a>Хөгжүүлэлтэнд оролцох

Энэхүү сантай холбоотой алдаа засвар, сайжруулалт болон бусад санал, хүсэлтийг нээлттэй хүлээж авах ба ялангуяа чанартай кодын өөрчлөлтүүд илгээвэл маш их баярлах болно.

Жич: Кодын өөрчлөлт оруулахдаа заавал тестийг нь хамт оруулахаа битгий мартаарай.

## <a id="license"></a>Лиценз

[MIT License](https://choosealicense.com/licenses/mit/)
