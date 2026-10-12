# KWERT Wear — kiyim do'koni sayti

Namangandagi premium unisex kiyim do'koni **KWERT** uchun bir sahifali sayt.

- 3D aylantiriladigan kiyim modeli (Three.js)
- [t.me/kwert_wear](https://t.me/kwert_wear) kanalidagi barcha mahsulotlar katalogi: filtr, qidiruv, saralash
- O'lcham, son va izoh tanlab savatchaga qo'shish
- Buyurtma tayyor xabar bilan [@kwert_admin](https://t.me/kwert_admin) Telegram lichkasiga yuboriladi
- Kargo kalkulyatori (100 gr = 14 000 so'm)
- Biz haqimizda: [Telegram](https://t.me/kwert_wear) · [Instagram](https://www.instagram.com/kwert.wear/) · [Otzivlar](https://t.me/kwert_otziv)

## Ishga tushirish

Hech qanday build kerak emas — `index.html` ni brauzerda oching yoki GitHub Pages orqali joylang
(Settings → Pages → Branch: `main`, folder: `/root`).

## Mahsulot qo'shish

`index.html` ichidagi `RAW` ro'yxatiga yangi qator qo'shing:

```
postRaqami|Nomi|turkum|narx|rasmlarSoni
```

Turkumlar: `hoodie`, `jacket`, `top`, `pants`, `shoes`, `acc`, `drop`.

## Rasmlar va ma'lumotlar avtomatik yangilanadi

`.github/workflows/sync.yml` har 6 soatda (va qo'lda: **Actions → Telegram kanaldan yangilash → Run workflow**)
`scripts/sync_telegram.py` ni ishga tushiradi. Skript t.me/kwert_wear kanalining barcha postlarini o'qiydi,
rasmlarni `images/` papkaga yuklaydi va narx, matn, rasmlar ro'yxatini `products.json` ga yozadi.
Sayt shu faylni o'qiydi — kanalga yangi post qo'yilsa, saytga o'zi qo'shiladi.
