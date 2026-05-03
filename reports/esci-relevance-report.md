# Product Search Relevance Report

Evaluated queries: 100
Baseline strategy: `baseline_bm25`

## Strategy Summary

| Strategy | Status | Evaluated Queries | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Delta nDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_bm25 | ok | 100 | 0.215 | 0.046 | 0.278 | 0.138 | +0.000 |
| boosted_bm25 | ok | 100 | 0.228 | 0.066 | 0.373 | 0.201 | +0.063 |
| enriched_profile | ok | 100 | 0.208 | 0.063 | 0.380 | 0.181 | +0.043 |

## Per-Query Results

| Query | Strategy | Winner | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Top Results |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| !awnmower tires without rims | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| !awnmower tires without rims | boosted_bm25 | yes | 0.000 | 0.000 | 0.100 | 0.010 | B001THCJDE, B01BWMK2OI, B014H1430K, B0756N728C, B0859NJFKN |
| !awnmower tires without rims | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B01BWMK2OI, B01ANIT126, B00ID51M9W, B014H1430K, B0859NJFKN |
| !qscreen fence without holes | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| !qscreen fence without holes | boosted_bm25 | yes | 0.200 | 0.067 | 0.200 | 0.085 | B082TZYKX4, B091TV7GL2, B01CDUJQIQ, B0001ZWZ8O, B08NG85RHL |
| !qscreen fence without holes | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B082TZYKX4, B004VQE1DG, B091CPZ39Z, B00INAW10G, B00KC65Z3E |
| # 10 self-seal envelopes without window | baseline_bm25 |  | 0.200 | 0.029 | 0.333 | 0.250 | B08Y8VX63W, B08V352RY5, B08Y8TWR38, B08CK95JS3, B071VC47NS |
| # 10 self-seal envelopes without window | boosted_bm25 | yes | 0.400 | 0.059 | 0.500 | 0.302 | B07R4TGNCF, B078S5ZL5D, B078HHGY2L, B06W5294BW, B007YX2KB8 |
| # 10 self-seal envelopes without window | enriched_profile |  | 0.200 | 0.029 | 0.500 | 0.268 | B08V352RY5, B078S5ZL5D, B071VC47NS, B0153SIHL2, B079H6L3CK |
| # 2 pencils not sharpened | baseline_bm25 | yes | 0.400 | 0.056 | 1.000 | 0.329 | B087J9MBXJ, B07Q391X7B, B07NH2D2CP, B06VSJ9LZ6, B072283ZL8 |
| # 2 pencils not sharpened | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B08DLXH86D, B088SZQY8R, B07PBT2K43, B075KKZSKC, B01FWSJQU4 |
| # 2 pencils not sharpened | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08158738F, B07RLBY1K2, B07ZQF4SCY, B07QPXWR15, B010WB6456 |
| # cellist thats not a hashtag | baseline_bm25 |  | 1.000 | 0.071 | 1.000 | 0.220 | B08J5KBGPP |
| # cellist thats not a hashtag | boosted_bm25 | yes | 1.000 | 0.357 | 1.000 | 1.000 | B08J5KBGPP, B096LZW7J1, B096LXN8QP, B096LXW2LJ, B096LXNCN3 |
| # cellist thats not a hashtag | enriched_profile |  | 0.800 | 0.286 | 1.000 | 0.763 | 1091347697, B0851M1499, 1092553924, 1677867973, B07NV8DB9Q |
| # do not disturb | baseline_bm25 | yes | 0.800 | 0.100 | 0.500 | 0.710 | B0935926GC, B0023LX6FK, B00DSZPCB6, B00EPKRHTI, B07K8XRWK2 |
| # do not disturb | boosted_bm25 |  | 0.800 | 0.100 | 0.500 | 0.640 | B0935926GC, B0023LX6FK, B00DSZPCB6, B00EPKRHTI, B07K8XRWK2 |
| # do not disturb | enriched_profile |  | 0.400 | 0.050 | 0.333 | 0.274 | B01M64Y71U, B08VRWTQ97, B08HVFJVXT, B08HVN9DSV, B08TB4QVGN |
| # mom life | baseline_bm25 | yes | 0.400 | 0.154 | 1.000 | 0.289 | B07P653H3H, B07P99MVHJ, B07D1B9126, B07T277YBN, B07S8MNZPR |
| # mom life | boosted_bm25 |  | 0.400 | 0.154 | 0.500 | 0.167 | B07T277YBN, B07P653H3H, B07P99MVHJ, B07D1B9126, B07S8MNZPR |
| # mom life | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07MDJP4SN, B00DYOQJV8, B00DYOQKJ4, B00DYOQKP8, B00DYOQLKM |
| # sharp not hashtag shirt | baseline_bm25 |  | 1.000 | 0.132 | 1.000 | 0.958 | B07KFSSV7K, B07MKLHJT4, B073X2GY3N, B07S9PFC38, B074T22KRC |
| # sharp not hashtag shirt | boosted_bm25 |  | 1.000 | 0.132 | 1.000 | 0.958 | B07KFSSV7K, B07MKLHJT4, B073X2GY3N, B07S9PFC38, B074T22KRC |
| # sharp not hashtag shirt | enriched_profile | yes | 1.000 | 0.132 | 1.000 | 1.000 | B07N4NBRC1, B07NV8DB9Q, B07PCQGJW5, B07XZSBWX7, B07KFSSV7K |
| #1 best and not expensive bath back brush cream color | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #1 best and not expensive bath back brush cream color | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B06X1BQ748, B07CH3X72J, B07GRDGZMZ, B07GRHVZPJ, B0171L4G64 |
| #1 best and not expensive bath back brush cream color | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B06X1BQ748, B0171L4G64, B07GRHVZPJ, B07CH3X72J, B07GRDGZMZ |
| #1 black natural hair dye without ammonia or peroxide | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07CKFPLQV |
| #1 black natural hair dye without ammonia or peroxide | boosted_bm25 | yes | 0.200 | 0.030 | 0.500 | 0.139 | B00BWVZ5YC, B07C4QR12V, B08SQQB7MV, B07D5RL5Y4, B0037XUGYC |
| #1 black natural hair dye without ammonia or peroxide | enriched_profile |  | 0.000 | 0.000 | 0.167 | 0.034 | B00X8M0M96, B0037XUGYC, B07KJQDVM4, B00BEWWCU4, B00BOEEX04 |
| #1 rated resveratrol supplement without tea leaves | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #1 rated resveratrol supplement without tea leaves | boosted_bm25 |  | 0.600 | 0.083 | 1.000 | 0.400 | B07Y8XPLK1, B083F5WC2P, B0069RN8YI, B07S391Y5Q, B01HDV6N6I |
| #1 rated resveratrol supplement without tea leaves | enriched_profile | yes | 0.800 | 0.111 | 1.000 | 0.588 | B07Y8XPLK1, B083F5WC2P, B08V1FLW6B, B07S391Y5Q, B07NRKDQPN |
| #1 selling shoes for men without shoeleases | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #1 selling shoes for men without shoeleases | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07GDQLRZM, B07GDRBMKK, B07NVRQWBY, B07GGHCY6H, B07FQF6986 |
| #1 selling shoes for men without shoeleases | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07FQF6986, B07FQMLNX6, B07FQPN3C5, B0871RT792, B07GDQLRZM |
| #1 small corded treadmill without remote control | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #1 small corded treadmill without remote control | boosted_bm25 | yes | 0.200 | 0.071 | 1.000 | 0.172 | B089CH6P5C, B08SBQRY3W, B0863LMHWZ, B07S5969LB, B08KXP3M2D |
| #1 small corded treadmill without remote control | enriched_profile |  | 0.200 | 0.071 | 1.000 | 0.106 | B089CH6P5C, B08N9V3MBJ, B08M5CG4H3, B08HCGJJJK, B089LMQ87D |
| #10 cans applesauce | baseline_bm25 |  | 1.000 | 0.125 | 1.000 | 0.381 | B00CF5AARQ |
| #10 cans applesauce | boosted_bm25 |  | 0.200 | 0.125 | 1.000 | 0.381 | B00CF5AARQ, B00T7CKW6Y, B07WDT3WM9, B0829FTMMP, B0967CYJ6H |
| #10 cans applesauce | enriched_profile | yes | 0.200 | 0.125 | 1.000 | 0.439 | B00CF5AARQ, B07WDT3WM9, B07C3435PP, B079J7QS6K, B0829FTMMP |
| #10 envelopes self seal | baseline_bm25 |  | 0.600 | 0.188 | 1.000 | 0.425 | B07R4TGNCF, B078HHGY2L, B078S5ZL5D, B06VVLD2GL, B01N175R8R |
| #10 envelopes self seal | boosted_bm25 |  | 0.400 | 0.125 | 1.000 | 0.423 | B07R4TGNCF, B078S5ZL5D, B078HHGY2L, B003BLQHYI, B07VBPZJV8 |
| #10 envelopes self seal | enriched_profile | yes | 0.600 | 0.188 | 1.000 | 0.466 | B078S5ZL5D, B08V3S1926, B08V3W382H, B07R4TGNCF, B016V06OYS |
| #10 envelopes without security tint | baseline_bm25 |  | 0.600 | 0.100 | 0.500 | 0.378 | B016V06OYS, B01D0OANU4, B085WJMWC9, B08Y8VX63W, B07CXXVXLC |
| #10 envelopes without security tint | boosted_bm25 | yes | 0.800 | 0.133 | 1.000 | 0.418 | B07R4TGNCF, B078S5ZL5D, B07GJKFC5X, B07GJCSF8Z, B08G14MTVW |
| #10 envelopes without security tint | enriched_profile |  | 0.400 | 0.067 | 1.000 | 0.311 | B01D0OANU4, B016V06OYS, B08V3W382H, B078S5ZL5D, B07R4TGNCF |
| #10 standard no tint no window not self seal | baseline_bm25 |  | 1.000 | 0.067 | 1.000 | 0.261 | B08CK95JS3 |
| #10 standard no tint no window not self seal | boosted_bm25 | yes | 0.200 | 0.067 | 1.000 | 0.343 | B078HHGY2L, B07RP3F2LW, B008005REQ, B08ZNLGLPF, B07GJKFC5X |
| #10 standard no tint no window not self seal | enriched_profile |  | 0.200 | 0.067 | 0.500 | 0.283 | B08Y97TG79, B08CK95JS3, B085VV4TV5, B06W5294BW, B071VC47NS |
| #10 window envelopes not self seal | baseline_bm25 | yes | 0.800 | 0.143 | 1.000 | 0.583 | B079H6L3CK, B07C28VWVN, B08CK95JS3, B06XDRJ316, B0797ZMZ9Q |
| #10 window envelopes not self seal | boosted_bm25 |  | 0.200 | 0.036 | 0.333 | 0.076 | B07R4TGNCF, B078S5ZL5D, B078HHGY2L, B07R2FCTJG, B06W5294BW |
| #10 window envelopes not self seal | enriched_profile |  | 0.200 | 0.036 | 0.333 | 0.252 | B08V352RY5, B078S5ZL5D, B079H6L3CK, B0153SIHL2, B071VC47NS |
| #10 window envelopes without plastic | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #10 window envelopes without plastic | boosted_bm25 |  | 0.200 | 0.029 | 1.000 | 0.284 | B07K4SGXRP, B078HHGY2L, B07RDNZ568, B081RD9MCZ, B086H5V1C2 |
| #10 window envelopes without plastic | enriched_profile | yes | 0.800 | 0.118 | 1.000 | 0.676 | B08V352RY5, B071VC47NS, B08Y8TWR38, B08CK95JS3, B01D0OANU4 |
| #11 mrs. kormel is not normal | baseline_bm25 | yes | 1.000 | 0.333 | 1.000 | 0.542 | 0060822295 |
| #11 mrs. kormel is not normal | boosted_bm25 |  | 0.200 | 0.333 | 1.000 | 0.542 | 0060822295, B074GFPD96, 1945446080, B00VWGB6S6, B071FRF9CJ |
| #11 mrs. kormel is not normal | enriched_profile |  | 0.200 | 0.333 | 1.000 | 0.542 | 0060822295, B00VWGB6S6, B00XPANEWS, B01JUCQHNC, B074GFPD96 |
| #12 black boys chain necklace without baseball stitches | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #12 black boys chain necklace without baseball stitches | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B083SBJLZ7, B077V1W2XZ, B07VTC243X, B01BNR4TD2, B01BNR4TGO |
| #12 black boys chain necklace without baseball stitches | enriched_profile | yes | 0.600 | 0.107 | 1.000 | 0.342 | B087JB9P67, B08LMVKCJ6, B07XQ9FBJ2, B08ZSYMVCH, B07LH1FZ52 |
| #14 x 1-1/2 stainless self tapping | baseline_bm25 |  | 0.750 | 0.188 | 1.000 | 0.454 | B07Y7XGLJL, B074ZXJK2P, B07X2H5Y2Y, B0128T2KX0 |
| #14 x 1-1/2 stainless self tapping | boosted_bm25 |  | 0.800 | 0.250 | 1.000 | 0.839 | B07Y7XGLJL, B07R6Y2MMH, B076BTTB9M, B086HMB4X7, B074ZXJK2P |
| #14 x 1-1/2 stainless self tapping | enriched_profile | yes | 0.800 | 0.250 | 1.000 | 0.849 | B07R6Y2MMH, B0128T2KX0, B074ZXJK2P, B07Y7XGLJL, B086HMB4X7 |
| #15 charm | baseline_bm25 |  | 0.400 | 0.125 | 1.000 | 0.419 | B07485GXBF, B011JI397C, B07SKLQ1G1, B010W5KQHY, B07BRQ16MF |
| #15 charm | boosted_bm25 | yes | 0.200 | 0.062 | 1.000 | 0.437 | B07485GXBF, B011JI397C, B07SKLQ1G1, B009E8NATC, B07CMRP13Y |
| #15 charm | enriched_profile |  | 0.200 | 0.062 | 1.000 | 0.126 | B07DFHQ6KY, B07RFHF2FV, B01ELP31Q4, B081N46TXR, B019MCJI54 |
| #2 dixon oriole pencils not sharpened | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #2 dixon oriole pencils not sharpened | boosted_bm25 | yes | 0.800 | 0.100 | 1.000 | 0.302 | B072DSDNH9, B00M3GFG76, B004X4KRDE, B011VB1OYC, B01FWSJQU4 |
| #2 dixon oriole pencils not sharpened | enriched_profile |  | 0.400 | 0.050 | 0.333 | 0.152 | B07ZQF4SCY, B08DLXH86D, B00M3GFG76, B072DSDNH9, B08DTFXYF5 |
| #2 pencils | baseline_bm25 | yes | 0.000 | 0.000 | 0.111 | 0.130 | B07Q5LJWNZ, B07G4672FN, B07B42FRWR, B07LF4JYD4, B07GBBRMV1 |
| #2 pencils | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B01FWSJQHC, B01FWSJRE4, B01FWSJQU4, B01FWSJS16, B088SZQY8R |
| #2 pencils | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B01FWSJQHC, B01FWSJQU4, B01FWSJRE4, B01FWSJS16, B01FWSJQZO |
| #2 pencils with erasers sharpened not soft | baseline_bm25 | yes | 0.600 | 0.077 | 0.500 | 0.449 | B087J9MBXJ, B0891SSBJT, B0891R2YFN, B07G2Q28PG, B07G2RYY6H |
| #2 pencils with erasers sharpened not soft | boosted_bm25 |  | 0.200 | 0.026 | 0.500 | 0.020 | B075KKZSKC, B01FWSJQU4, B08R8LW1W2, B01FWSJQZO, B01FWSJSJ8 |
| #2 pencils with erasers sharpened not soft | enriched_profile |  | 0.000 | 0.000 | 0.167 | 0.078 | B08158738F, B07RLBY1K2, B07ZQF4SCY, B07QPXWR15, B08ZCDH33N |
| #2 pencils without erasers | baseline_bm25 |  | 0.600 | 0.083 | 1.000 | 0.418 | B01GPJXPQ0, B00MI50TYM, B07R3F2MH4, B06XGPLVH7, B07RQVZHL6 |
| #2 pencils without erasers | boosted_bm25 | yes | 1.000 | 0.139 | 1.000 | 0.782 | B01FWSJRE4, B01FWSJS16, B01FWSJQZO, B01FWSJSJ8, B01FWSJQHC |
| #2 pencils without erasers | enriched_profile |  | 0.000 | 0.000 | 0.167 | 0.282 | B07DPVVMWB, B082H9Y8GV, B081DN445R, B00PGNSC92, B082GZHGF5 |
| #20 paper bags without handle | baseline_bm25 |  | 0.400 | 0.071 | 1.000 | 0.147 | B095XWN82Z, B07S2LV1QC, B081YQ4XVQ, B07D6L24GF, B0876P47ZF |
| #20 paper bags without handle | boosted_bm25 |  | 0.200 | 0.036 | 0.333 | 0.145 | B085ZL8ZCX, B09BBNC9RG, B083LKWCNR, B08L929P16, B07ZNF3XPB |
| #20 paper bags without handle | enriched_profile | yes | 0.600 | 0.107 | 1.000 | 0.272 | B07H3PSRVX, B07SZGQFZS, B095XWN82Z, B07V5LLCV4, B07XL96PF2 |
| #3 metal zipper slider not made in america | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #3 metal zipper slider not made in america | boosted_bm25 |  | 0.400 | 0.065 | 1.000 | 0.376 | B01M4IFK18, B013XF8T2Y, B01MUVI9PV, B07QQXBPKQ, B07PM1XH37 |
| #3 metal zipper slider not made in america | enriched_profile | yes | 0.600 | 0.097 | 1.000 | 0.567 | B07THSNBBW, B07PM1XH37, B07QQXBPKQ, B005I5JA2G, B07BMZ52G8 |
| #4 braiding hair not stretched | baseline_bm25 |  | 0.000 | 0.000 | 0.143 | 0.123 | B087CG1CMT, B07D1292ZB, B07FFLQDTN, B0894JSC8T, B07K6MX269 |
| #4 braiding hair not stretched | boosted_bm25 |  | 0.000 | 0.000 | 0.143 | 0.031 | B07ZGD7ZVS, B07W48T2F5, B07FXL6YH9, B07DG2RX7F, B087CG1CMT |
| #4 braiding hair not stretched | enriched_profile | yes | 0.200 | 0.032 | 1.000 | 0.161 | B07YXX1XGZ, B08J7L9SRF, B087CG1CMT, B07WGV271P, B0894JSC8T |
| #4 pads without wings | baseline_bm25 |  | 0.800 | 0.129 | 1.000 | 0.594 | B01IAI9WNO, B0029NYQME, B01IAIA95O, B001G7QUZU, B084H3MY2N |
| #4 pads without wings | boosted_bm25 | yes | 1.000 | 0.161 | 1.000 | 0.855 | B0052RF17S, B01IAI9WNO, B007X4SZZI, B0029NYQME, B01IAIA95O |
| #4 pads without wings | enriched_profile |  | 0.800 | 0.129 | 1.000 | 0.495 | B01N7HMX75, B01IAI6SD6, B001E6KHAW, B01IULAV6I, B0029NYQME |
| #5 coil zipper without lock | baseline_bm25 |  | 1.000 | 0.125 | 1.000 | 0.202 | B07QFN6B8F, B07Q1YHWL3, B0999PFCDV, B08G8W3SJ2 |
| #5 coil zipper without lock | boosted_bm25 | yes | 0.600 | 0.094 | 1.000 | 0.514 | B08NGL8268, B07CG4Z7Q8, B00506SQPA, B08Y7R9TL5, B08S3HH74K |
| #5 coil zipper without lock | enriched_profile |  | 0.800 | 0.125 | 1.000 | 0.480 | B07QFN6B8F, B08PD7BTNT, B08HS2X9YM, B07DFZ12RK, B0999PFCDV |
| #5 machine screws | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07XVN7RMB, B07FR24XNP, B0991YJJ9G, B07PD5L5XR, B01MR892S8 |
| #5 machine screws | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07HLJ97J6, B00004YOBF, B00JKDFYQ8, B01BXKETRA, B07HD1M85F |
| #5 machine screws | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B00WEFVUNK, B07H3K5NQ2, B0795M5L6X, B00JKDFYQ8, B08BHXFBMP |
| #5 orb to not fitting | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07B2YQLBL, B07CVW2HGH, B07CVW9MB8, B07WCHKKNT, B00PVE19SW |
| #5 orb to not fitting | boosted_bm25 |  | 0.400 | 0.222 | 1.000 | 0.468 | B08LPC9JTB, B089F8HBFQ, B07X9YCGPT, B07V27X9SB, B08BFMZC32 |
| #5 orb to not fitting | enriched_profile | yes | 0.600 | 0.333 | 1.000 | 0.540 | B07V27X9SB, B078Z4CV2J, B07NHX8R9M, B08LPC9JTB, B07DXSCVD4 |
| #5 pull cord | baseline_bm25 | yes | 0.200 | 0.091 | 0.200 | 0.101 | B00JIBITGY, B07GXG2NDG, B07VN7VTGD, B004QGXND0, B07CF7D36C |
| #5 pull cord | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07GXG2NDG, B00JIBITGY, B01FHGG7YO, B08V5PDWPM, B07VGV2RPP |
| #5 pull cord | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07N4BY7TD, B07VGV2RPP, B01LYZIJAP, B00M5T8EGG, B000BVXVTA |
| #5 zipper tape without pulls | baseline_bm25 | yes | 0.600 | 0.100 | 1.000 | 0.396 | B08PD7BTNT, B07QFN6B8F, B07Q1YHWL3, B0895CW8P4, B0999PFCDV |
| #5 zipper tape without pulls | boosted_bm25 |  | 0.600 | 0.100 | 1.000 | 0.269 | B08PS3YWBS, B097NZ57N1, B08PD7BTNT, B08S3HH74K, B082SQY8RQ |
| #5 zipper tape without pulls | enriched_profile |  | 0.800 | 0.133 | 1.000 | 0.378 | B08PD7BTNT, B07QFN6B8F, B08Z8B1XVL, B07ZPFH3CT, B074CMMFXH |
| #6 fishing hook without barb | baseline_bm25 |  | 0.600 | 0.097 | 1.000 | 0.397 | B07T7PB8CN, B07GQY4ZBG, B0891X23M3, B081N13H7V, B07MFKM5VJ |
| #6 fishing hook without barb | boosted_bm25 | yes | 0.800 | 0.129 | 1.000 | 0.441 | B07N63KDNN, B07F1LDRQ3, B08QF4K6JN, B07T7PB8CN, B07R7QKM8M |
| #6 fishing hook without barb | enriched_profile |  | 0.200 | 0.032 | 0.500 | 0.091 | B078SR9N3S, B07T7PB8CN, B01D60X92Q, B078SQ2FHS, B078SQ8FM6 |
| #68 do not fuplicate key | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #68 do not fuplicate key | boosted_bm25 |  | 0.200 | 0.143 | 1.000 | 0.449 | B00HJAGSB4, B07QZLW8PF, B083LFTLLT, B0836Q88KT, B07CHNNC8Z |
| #68 do not fuplicate key | enriched_profile | yes | 0.400 | 0.286 | 1.000 | 0.557 | B00HJAGSB4, B008IVNJK6, B07Z3F88WV, B00NLMWWN2, B07PNRF17V |
| #8 merchandising tags without string | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #8 merchandising tags without string | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B0979Z13W9, B076BBJYRN, B091GJTZ8Y, B013ORWB7K, B013ORWBC0 |
| #8 merchandising tags without string | enriched_profile | yes | 0.200 | 0.030 | 0.500 | 0.139 | B07541MJRV, B00I0EU22Y, B01JH4H9K8, B07HRYGN97, B07QNTWLQS |
| #8 phillips head wood screws | baseline_bm25 | yes | 0.400 | 0.125 | 1.000 | 0.583 | B07GDQ9LRN, B08545BSYB, B084Y8N6M8, B07L3ZY3Z9, B07L4BSVDV |
| #8 phillips head wood screws | boosted_bm25 |  | 0.600 | 0.188 | 0.500 | 0.437 | B08HXZG71X, B075DJ2R9Z, B07DDK12GD, B07D1KGR2P, B07D1KL6SR |
| #8 phillips head wood screws | enriched_profile |  | 0.000 | 0.000 | 0.111 | 0.066 | B08HXZG71X, B08LBB342P, B089KGSZTD, B07ZWPG2QL, B07ZWDBFF6 |
| #8 tags without string | baseline_bm25 |  | 0.800 | 0.125 | 1.000 | 0.310 | B076BBJYRN, B00I0EU22Y, B00OLNG12I, B07FNCSY6B, B07541MJRV |
| #8 tags without string | boosted_bm25 | yes | 0.600 | 0.094 | 0.500 | 0.551 | B0979Z13W9, B076BBJYRN, B091GJTZ8Y, B013ORWB7K, B013ORWBC0 |
| #8 tags without string | enriched_profile |  | 0.600 | 0.094 | 1.000 | 0.299 | B07541MJRV, B00I0EU22Y, B07QNTWLQS, B00OLNG12I, B076BBJYRN |
| #82 jewelry box without cotton | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #82 jewelry box without cotton | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B007PKHGSC, B07GZ22SBF, B07GZY3XK6, B073VCX525, B07GY3PGMP |
| #82 jewelry box without cotton | enriched_profile | yes | 0.200 | 0.038 | 0.333 | 0.138 | B07N8NS2BK, B01N6QTL9D, B084KWVQBL, B007PKHGSC, B07GY3PGMP |
| #9x5" wood screws | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #9x5" wood screws | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B01L9VCO9S, B07ZWGDV6V, B07N6LY3B4, B07ZWC5QR2, B07ZWDHH2G |
| #9x5" wood screws | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08HXZG71X, B07ZWDBFF6, B07ZWGDV6V, B07ZWDHH2G, B07ZWPG2QL |
| #do not disturb, jeidah bila | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #do not disturb, jeidah bila | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B0935926GC, B0023LX6FK, B00DSZPCB6, B00EPKRHTI, B07K8XRWK2 |
| #do not disturb, jeidah bila | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B01M64Y71U, B08VRWTQ97, B08HVFJVXT, B08HVN9DSV, B08TB4QVGN |
| #followme ultra soft velour robe without hood for men | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #followme ultra soft velour robe without hood for men | boosted_bm25 |  | 0.200 | 0.028 | 1.000 | 0.242 | B07CS9N7YZ, B01N5PBXV2, B082PB4TCH, B082PBPTGS, B082PBJVT1 |
| #followme ultra soft velour robe without hood for men | enriched_profile | yes | 0.600 | 0.083 | 1.000 | 0.328 | B07CS9N7YZ, B06ZYWRNN5, B071R66NRP, B071Y5SFYP, B082PBPTGS |
| #hydrate not dydrate | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #hydrate not dydrate | boosted_bm25 |  | 0.000 | 0.000 | 0.111 | 0.080 | B088ZZYMK2, B076CSLPM1, B07S64FKYS, B07S6SPNKB, B07S6SQYRT |
| #hydrate not dydrate | enriched_profile | yes | 0.200 | 0.125 | 0.500 | 0.167 | B07176PR7D, B08W9GF9HD, B07T73LJFM, B09C6LPGGB, B07BVV4VJZ |
| #i am not chinese | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | 753548672X, B00Y1NQW2M, B08L6PDSR4, B07JHFQ5C2, B07SGB52DT |
| #i am not chinese | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | 753548672X, B00Y1NQW2M, 0998434981, 1094000337, B0829G7B1V |
| #i am not chinese | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | 753548672X, B07JZNTTVR, B00Y1NQW2M, B08WDKBL6P, B08WLGDPHB |
| #i may not look like diesel decals | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #i may not look like diesel decals | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07VT2RH2K, B07T5LZ9NM, B07DH63QKF, B07P54QYXG, B07P5C72BQ |
| #i may not look like diesel decals | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07VT2RH2K, B07GH3DT35, B07KK38QWJ, B07P54QYXG, B07T5LZ9NM |
| #metoo not you | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07GV9R83F, B07NPCRPX8, B011XNACNM, B08JQL87YF |
| #metoo not you | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | 0446555711, 0446530778, 0446615404, 1609412540, B08KNMYS6W |
| #metoo not you | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07MVMYJ3N, B07HJC95HC, B088T9WF5K, B07226BMJK, B07ZTKLHSQ |
| #pinkandproud not sorry glitter lipstick | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| #pinkandproud not sorry glitter lipstick | boosted_bm25 | yes | 0.800 | 0.105 | 1.000 | 0.414 | B07SM3G7KV, B07BFVLMVY, B07LD6YB1Q, B078BTB69Z, B09C59LKSV |
| #pinkandproud not sorry glitter lipstick | enriched_profile |  | 0.600 | 0.079 | 0.500 | 0.352 | B08GZ1FK71, B078BTB69Z, B08LYP272Y, B07R7V7XLN, B08LYD6R9R |
| #stuccoville life without a net | baseline_bm25 | yes | 1.000 | 1.000 | 1.000 | 1.000 | 194796643X |
| #stuccoville life without a net | boosted_bm25 |  | 0.200 | 1.000 | 1.000 | 1.000 | 194796643X, B094XDCPP2, 1625915098, 169516721X, B07N7G27WC |
| #stuccoville life without a net | enriched_profile |  | 0.200 | 1.000 | 1.000 | 1.000 | 194796643X, B094XDCPP2, 1625915098, 169516721X, B07N7G27WC |
| #this is not a truck decals | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07S2LR84F, B01M5K3KSA, B0838HCGSF, B00KVOGGEY, B097SQ67G9 |
| #this is not a truck decals | boosted_bm25 | yes | 0.600 | 0.130 | 0.500 | 0.282 | B07TTTLXV2, B08N6JL9Q4, B018H3P6HI, B018H3TRIW, B07HNDPWZW |
| #this is not a truck decals | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B0838HCGSF, B07S2LR84F, B097SQ67G9, B083B74LYL, B07K3C7381 |
| #try not to suck tshirt | baseline_bm25 |  | 1.000 | 0.100 | 1.000 | 0.406 | B07PJZRNBJ, B07KVR6LVV, B07FQKM692 |
| #try not to suck tshirt | boosted_bm25 | yes | 1.000 | 0.167 | 1.000 | 1.000 | B07PJZRNBJ, B07N1QP7JH, B07L13CZNL, B07PLF6HB9, B07KDRHCZ8 |
| #try not to suck tshirt | enriched_profile |  | 0.600 | 0.100 | 1.000 | 0.392 | B07FQKM692, B07KVR6LVV, B08LT9V4JG, B08LTDNDLL, B07L13CZNL |
| $0.00 not kindleunlimited | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $0.00 not kindleunlimited | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B06XHXJG31, B07XPD9L1C, B087M6PVKW, B07GBXPM3L, B072ZWC9FT |
| $0.00 not kindleunlimited | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B06XHXJG31, B07XPD9L1C, B087M6PVKW, B07GBXPM3L, B07T8YFTM6 |
| $1 | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B08V1PTQMK, B000BO8EE4, B004VTG2W6, B0785PY1H2, B072LY5TYH |
| $1 | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B08V1PTQMK, B000BO8EE4, B004VTG2W6, B0785PY1H2, B072LY5TYH |
| $1 | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08V1PTQMK, B000BO8EE4, B004VTG2W6, B0785PY1H2, B072LY5TYH |
| $1 dollar toys not fidgets | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $1 dollar toys not fidgets | boosted_bm25 | yes | 0.200 | 0.111 | 0.200 | 0.096 | B0932MBF2K, B091CC7JX4, B08S6T5NTH, B07PW98XXR, B08LNGFYGJ |
| $1 dollar toys not fidgets | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08MT7NRG2, B08NJ9C1J8, B097ZD2L2R, B091CHD1VV, B0936KJQYY |
| $1 first addition charizard not fake | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $1 first addition charizard not fake | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07G7246X6, B07TX374HW, B076BCLWJB, B074PDN95B, B09HXW1VV3 |
| $1 first addition charizard not fake | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07TX374HW, B076BCLWJB, B074PDN95B, B09HXW1VV3, B074MGFBRW |
| $1 items for men | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07BL5JXR1, B00LCXBDWS, B08B55ZF7Z, B088P94548, B083HVLSVX |
| $1 items for men | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B01L9KUFJA, B07BL5JXR1, B07W21HN2G, B07RW58SFH, B07JZ715MF |
| $1 items for men | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B088P94548, B007WVIBQA, B07MGQF535, B08CZVRCJ2, B07XF54FNH |
| $1 million that look real but that is not it | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B0757K4F6K, B076SL392C, B07PM22PWZ, B019MMUA8S, B0822DSQ1P |
| $1 million that look real but that is not it | boosted_bm25 |  | 0.200 | 0.125 | 0.333 | 0.140 | B08L6LR8PR, B002HESJBY, B00FGXSE36, B07TZLH2SP, B07YY1764T |
| $1 million that look real but that is not it | enriched_profile | yes | 0.200 | 0.125 | 1.000 | 0.279 | B00FGXSE36, B07YY1764T, B00EMX9QPQ, B07DCZW39L, B07TZLH2SP |
| $1 stuffed toy | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B01ASZ0146, B01LWQA4LE, B00362TPXC, B00286CY2G, B007B5GW18 |
| $1 stuffed toy | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07G2HYY4M, B014PJQNI4, B07P2H63Y4, B08JY8L1C5, B01NCWDO96 |
| $1 stuffed toy | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B01COH2R98, B01CO8HI1O, B096P9DSPC, B07TKJ15RB, B07P2H63Y4 |
| $10 amazon prime not prime wardrobe sweatpaants | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $10 amazon prime not prime wardrobe sweatpaants | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B0767ZC9P9, B07N5MGKTY, B00S1UGM0S, B00XZ8C60Q, B00S1UH0I6 |
| $10 amazon prime not prime wardrobe sweatpaants | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07N5MGKTY, B01IVOD3VY, B01N9KIKZA, B07SL294WH, B00S1UGM0S |
| $10 blanket | baseline_bm25 | yes | 0.000 | 0.000 | 0.167 | 0.142 | B087TRPMTD, B07YSZKMNK, B08432MRX6, B07D35VCMM, B07Y8WV83K |
| $10 blanket | boosted_bm25 |  | 0.000 | 0.000 | 0.125 | 0.069 | B06XDJ2QVW, B087TRPMTD, B08VGJ6XW8, B07YSZKMNK, B08432MRX6 |
| $10 blanket | enriched_profile |  | 0.200 | 0.062 | 0.333 | 0.110 | B08KTH1JSC, B08432MRX6, B08BJG8S76, B08FRT9M4B, B07HCM6BVY |
| $10 candles | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07QHL8JLX, B07N99PTQ1, B01BNV7OZS, B07GBWFHF9, B0092RSKRW |
| $10 candles | boosted_bm25 | yes | 0.000 | 0.000 | 0.100 | 0.075 | B01D3IH562, B07XQNLSTX, B07N99PTQ1, B07YN82B6F, B0812BLK3W |
| $10 candles | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B082T2FHSX, B077LJ5QLK, B00MKKKCN8, B008CU2WFG, B009AM64KY |
| $10 credit not given on purchase on prime day | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $10 credit not given on purchase on prime day | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07SM9XHJW, B00HSDG8OY, B07DG1ZZQF, B07CVWYTPQ, B00WSAOTZW |
| $10 credit not given on purchase on prime day | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B00HSDG8OY, B07SM9XHJW, B07X13GR6Z, B07XBPSZRR, B00WSAOTZW |
| $10 gold eagle | baseline_bm25 | yes | 0.400 | 0.133 | 0.333 | 0.561 | B0000AUY86, B01DUSCZ42, B082DN3P3G, B07B2KQCPJ, B087BF4R46 |
| $10 gold eagle | boosted_bm25 |  | 0.400 | 0.133 | 0.333 | 0.362 | B0000AUY86, B01DUSCZ42, B082DN3P3G, B07B2KQCPJ, B087BF4R46 |
| $10 gold eagle | enriched_profile |  | 0.800 | 0.267 | 1.000 | 0.554 | B07BLNLW2F, B07Q4FJXC8, B089NL8GR3, B07Q5HKNWB, B07L443MN7 |
| $10 lol literally not gonna change baby pet lol | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $10 lol literally not gonna change baby pet lol | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B091TCD7MQ, B08HM4TRTC, B08QZ4LSQ3, B08DLF165G, B08P41T13J |
| $10 lol literally not gonna change baby pet lol | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B091TCD7MQ, B08HM4TRTC, B08QZ4LSQ3, B08P41T13J, B07JFRVFPG |
| $10 magnetic eyelashes without eyeliner | baseline_bm25 | yes | 0.400 | 0.065 | 1.000 | 0.356 | B0972WCZP2, B092CSHCJ4, B099DY9D11, B083NSC7HD, B089G6V2B9 |
| $10 magnetic eyelashes without eyeliner | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07FNXBDY3, B07VDB82VD, B093PTN439, B09DXXP5GH, B094R9GJXC |
| $10 magnetic eyelashes without eyeliner | enriched_profile |  | 0.200 | 0.032 | 0.200 | 0.171 | B092CSHCJ4, B083NSC7HD, B0897ZRZ7S, B08HT2L7L1, B094D5NQ35 |
| $10 stuff not books | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B089VX5XF4, B07QFRS1PL, B078W2ZC7M, B01MZILMY4, B0765ND1VC |
| $10 stuff not books | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07M747YKM, 0763644315, B07HHGTC7C, B06Y4SG383, B01DQX2RJY |
| $10 stuff not books | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07CYLC2BF, B07K2JL69K, B07K2KJFTW, B07KCL992V, B06Y4SG383 |
| $100 things that are not electronics | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07VF314GK, B00KTWY1DQ, B07JYJ5ZGL, B01GOXCIJM, B01LZYBPYV |
| $100 things that are not electronics | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | 1937578313, B078JNBVFY, B007PCNN78, B07JM18GL7, B01LZ8PDAG |
| $100 things that are not electronics | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07V5G1X15, 1937578313, B078JNBVFY, B07FLJT72Q, B07RJQHD3Q |
| $11 fidget please just please $11 not 25 not | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $11 fidget please just please $11 not 25 not | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B017TCGID4, B017TCL4EM, B017TCMF22, B01LXZJY7S, B079391J47 |
| $11 fidget please just please $11 not 25 not | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B0963D4V99, B082MSQ13D, B081YPCHZR, B084MC5VKT, B08V6HT65K |
| $12 label maker that’s not a cheap one | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $12 label maker that’s not a cheap one | boosted_bm25 |  | 0.200 | 0.067 | 0.333 | 0.110 | B07H9CV5TJ, B078JVDTZP, B08D7J1S34, B08F21XH53, B08JBX5KMZ |
| $12 label maker that’s not a cheap one | enriched_profile | yes | 0.200 | 0.067 | 1.000 | 0.220 | B08ZCMYT82, B0757JG57P, B07585ZGQR, B07XXB2MXN, B07H9CV5TJ |
| $13 bb guns without a yellow tube | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $13 bb guns without a yellow tube | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B00K1NAA6U, B0179SSDMC, B06XPF9HSZ, B0179TIL3W, B00GLV3VBC |
| $13 bb guns without a yellow tube | enriched_profile | yes | 0.200 | 0.029 | 0.333 | 0.082 | B00K1NAA6U, B0179SSDMC, B008DQ9VV2, B07VYP35Y1, B06XPF9HSZ |
| $13 fidget toys without paying for delivery | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $13 fidget toys without paying for delivery | boosted_bm25 | yes | 0.000 | 0.000 | 0.111 | 0.066 | B094N3CPHH, B07Q8QDVL5, B092V8LC9Y, B0936KJQYY, B094H4BG4Z |
| $13 fidget toys without paying for delivery | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B094N3CPHH, B097ZD2L2R, B07Q8QDVL5, B08MT7NRG2, B08NJ9C1J8 |
| $139 one cup cousy not coffee maker | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $139 one cup cousy not coffee maker | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07MX87HH9, B07ZHNDYDY, B08RHMMP9T, B08RHVYR85, B088TH196W |
| $139 one cup cousy not coffee maker | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B088TH196W, B0746DV91S, B092VSBR18, B07L96HRC8, B0899C1R7M |
| $15 doller bb guns not spring powered | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $15 doller bb guns not spring powered | boosted_bm25 | yes | 0.000 | 0.000 | 0.167 | 0.034 | B08X4F4FQH, B01GPJDVQE, B0199QUK3M, B07NVMRPCW, B004B1MTSK |
| $15 doller bb guns not spring powered | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07VYP35Y1, B00KBZTCOY, B01GPJDVQE, B008DQ9VV2, B0199QUK3M |
| $15 fidget pack without the pea poppet | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $15 fidget pack without the pea poppet | boosted_bm25 | yes | 0.400 | 0.091 | 0.333 | 0.238 | B08MT7NRG2, B08NJ9C1J8, B0936KJQYY, B093Q6QFM6, B091H2SHFC |
| $15 fidget pack without the pea poppet | enriched_profile |  | 0.400 | 0.091 | 0.333 | 0.227 | B08MT7NRG2, B08NJ9C1J8, B093Q6QFM6, B091H2SHFC, B0936KJQYY |
| $150 laptop not previews | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $150 laptop not previews | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07Y53N349, B07BLNVZ7D, B015EJPK42, B07N4J6T3F, B083BVLM71 |
| $150 laptop not previews | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | 1643696386, 1643696394, 1643696343, B00505DU4I, B07T1PH25B |
| $175 gram led frisbee gram not dollar | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $175 gram led frisbee gram not dollar | boosted_bm25 |  | 0.200 | 0.050 | 0.250 | 0.158 | B06XG1HTYY, B06XG4KZ7W, B0135RWTDK, B08WRZQCWM, B01944SOKA |
| $175 gram led frisbee gram not dollar | enriched_profile | yes | 0.400 | 0.100 | 1.000 | 0.204 | B004ZLB91O, B01LVZC319, B08WRZQCWM, B0135RWTDK, B00F2GZD68 |
| $2 pop tube not a pack | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07HWVM3S1, B07JQC4L12, B07JQCT8ZX, B07JYG28TT, B0867CYY8J |
| $2 pop tube not a pack | boosted_bm25 |  | 0.200 | 0.048 | 0.333 | 0.049 | B01NABA2ZA, B0963F1R3X, B097ZD2L2R, B07MW4T5DY, B0797N98B1 |
| $2 pop tube not a pack | enriched_profile | yes | 0.000 | 0.000 | 0.167 | 0.255 | B009CQTZMC, B01NABA2ZA, B0936KJQYY, B095NNWZ3M, B0095IGRIM |
| $20 not credible dog pool rectangular | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $20 not credible dog pool rectangular | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07Z31NQ1Q, B0983MX135, B07N52NLC3, B083FWYBW4, B089B7LMGF |
| $20 not credible dog pool rectangular | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B0983MX135, B07N52NLC3, B083FWYBW4, B07XKW55KJ, B085VFBZRY |
| $20 off for amazon app not applied | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07TMKZ9QL, B07NXR75HQ |
| $20 off for amazon app not applied | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B079JKPLM5, B06XGRXB4Q, B07Y4ZNJTX, B07TMKZ9QL, B078GDFYTY |
| $20 off for amazon app not applied | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B079JKPLM5, B08F2V9KVD, B07Y4ZNJTX, B078GDFYTY, B07TMKZ9QL |
| $20 rectangular not inflatable pool 26 i | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $20 rectangular not inflatable pool 26 i | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B08RYC8SNZ, B0897FLLKW, B0863PFPDV, B00W601ZJW, B089WH7BKD |
| $20 rectangular not inflatable pool 26 i | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08RYC8SNZ, B009HUAHAM, B089D17K9P, B089Y33V2L, B0887X1ZVX |
| $20 vr headset without controller | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07ZVYC41L, B081S1TV5M, B077BBLFF2, B086M2X2QR |
| $20 vr headset without controller | boosted_bm25 | yes | 0.200 | 0.083 | 0.333 | 0.229 | B07VRN1681, B07HH1FHHX, B08P1V69PJ, B0939LQQ54, B07HMKC45Y |
| $20 vr headset without controller | enriched_profile |  | 0.400 | 0.167 | 0.333 | 0.132 | B08RB2D8ST, B0863MT183, B07VDJDMLV, B08P1V69PJ, B07D8N1N2C |
| $230 pool for outdoors not plastic | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $230 pool for outdoors not plastic | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B08794Q43R, B093D6S49T, B073JF4TM3, B004M05IK6, B01HD7FPHK |
| $230 pool for outdoors not plastic | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B0855XTLRP, B0855Y7DKF, B0888SG554, B085C8LYF1, B0855YL82Y |
| $25 apple gift card not email | baseline_bm25 |  | 0.500 | 0.056 | 0.500 | 0.164 | B08F3BV69X, B08F3C99KN |
| $25 apple gift card not email | boosted_bm25 |  | 0.200 | 0.056 | 0.333 | 0.130 | B08NTQWTWN, B08F3BV69X, B08F3C99KN, B01B25L15E, B083HT9RSG |
| $25 apple gift card not email | enriched_profile | yes | 0.200 | 0.056 | 0.500 | 0.243 | B08F3BV69X, B08F3C99KN, B075Y8WBTS, B07Y453383, B07Y454LKQ |
| $25 ceiling fan without lights | baseline_bm25 |  | 0.200 | 0.033 | 0.200 | 0.085 | B08224PMYG, B08JCNBX6D, B07XP1XYHD, B081SVK95V, B08M189CNL |
| $25 ceiling fan without lights | boosted_bm25 | yes | 0.200 | 0.033 | 0.200 | 0.261 | B092TR6VS5, B09C1JPT3B, B0917GF8NH, B08JLRP5BH, B095HXZMQG |
| $25 ceiling fan without lights | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07VF3V52Y, B09H2YH2HT, B091YP6NCN, B095SHJWM8, B07KRTK7GQ |
| $25 katana swords not real | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $25 katana swords not real | boosted_bm25 |  | 0.200 | 0.029 | 0.250 | 0.095 | B08P1BYRTF, B07219NS51, B07NCGHJ3F, B097PBHXTH, B0893TVBLY |
| $25 katana swords not real | enriched_profile | yes | 0.200 | 0.029 | 0.250 | 0.173 | B07NCGHJ3F, B07TVCS3W8, B08P1BYRTF, B08CRYBFJ7, B07PPP7LX4 |
| $25 xbox gift card not digital | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B01HT1BW0E |
| $25 xbox gift card not digital | boosted_bm25 | yes | 0.600 | 0.333 | 0.333 | 0.520 | B00F4CF39C, B07C438TMN, B00F4CEHNK, B00F4CEOS8, B00F4CEWOY |
| $25 xbox gift card not digital | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B00F4CF39C, B07FMJVVKW, B0727VWRHF, B014S24B28, B081R3QMN2 |
| $275 airsoft guns | baseline_bm25 | yes | 1.000 | 0.200 | 1.000 | 0.359 | B015OVSLQO, B009NNALEU |
| $275 airsoft guns | boosted_bm25 |  | 0.200 | 0.100 | 1.000 | 0.220 | B009NNALEU, B0725G71JQ, B00C185NRO, B00GMAAUVG, B0002J836C |
| $275 airsoft guns | enriched_profile |  | 0.400 | 0.200 | 1.000 | 0.359 | B015OVSLQO, B009NNALEU, B07ZPDDZN8, B07VPLWX6J, B07BHNGRKN |
| $3 nail tips without tax | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $3 nail tips without tax | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B089Y2KLZ5, B085HKCVND, B07M8TZZJM, B00RGHKZUA, B0865W2MRK |
| $3 nail tips without tax | enriched_profile | yes | 0.000 | 0.000 | 0.111 | 0.066 | B0925Q72ZL, B0836S1MXY, B088Q1B9R8, B07M8TZZJM, B085HKCVND |
| $30 roblox gift card not digital | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $30 roblox gift card not digital | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B00F4CF4PU, B084LNGNX8, B08QCLF97N, B07Y94W69D, B0919XFLGP |
| $30 roblox gift card not digital | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08CNBCWCF, B09BKRJ5JJ, B08P2MPYWN, B07S294N8G, B087JLF2R6 |
| $35 bay casting left handed pole that does not do backlash | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $35 bay casting left handed pole that does not do backlash | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07XNFCF6T, B071YL7DX9, B083XH17J9, B01MRQCENJ, B01N46UYTL |
| $35 bay casting left handed pole that does not do backlash | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07WRN3HZ6, B07ZCD5BRP, B07ZCCGB3V, B06XYHR4N7, B08WZ5FWJ4 |
| $3what can you buy without siri dollar toy | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $3what can you buy without siri dollar toy | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B0797FZW44, B072PXP8CR, B07WNCP3HG, B07F34H6LM, B07V7ZZWCW |
| $3what can you buy without siri dollar toy | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B089M6N2ZM, B08QFLP8B8, B0797FZW44, B072PXP8CR, B07JCX7MB7 |
| $4 worthy items not books | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B01BJ484EO, B07MPVCCSN, B07MKKT12R, B08C5B4MSW |
| $4 worthy items not books | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B00GT0LZMM, B0000GHNUE, 9123939559, B08RGJ9S65, 1620105942 |
| $4 worthy items not books | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07YZVLVH4, B07DFTMDJT, B07Z4KXLW3, B07D2N9K1S, B07R3HCL96 |
| $40 bean bag chair for adults with bean not included | baseline_bm25 |  | 0.500 | 0.061 | 0.333 | 0.205 | B07D3NPM7T, B08ZXML5YZ, B08DP3RQ3T, B08T64J84T |
| $40 bean bag chair for adults with bean not included | boosted_bm25 | yes | 0.600 | 0.091 | 1.000 | 0.469 | B07L6GL9Z2, B07B9DT6NK, B08T64J84T, B00P21XE7I, B00P21YGDE |
| $40 bean bag chair for adults with bean not included | enriched_profile |  | 0.400 | 0.061 | 1.000 | 0.453 | B08T64J84T, B015QJJD34, B0821XTHP2, B0821WY8H9, B0821XN92W |
| $44red ' phone without having to pay production | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $44red ' phone without having to pay production | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07RZDZDFY, B07YC5XGZZ, B07YD5LLLZ, B0897HB4RX, B07PYZL3SC |
| $44red ' phone without having to pay production | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07RZDZDFY, B07D7KRQVB, B0897HB4RX, B07YC5XGZZ, B07PYZL3SC |
| $5 items | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07YRW6Z1K, B009LMJH1G, B07RRYBTCL, B082CW9YT9, B0924TSLJ3 |
| $5 items | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07YRW6Z1K, B009LMJH1G, B07RRYBTCL, B082CW9YT9, B0924TSLJ3 |
| $5 items | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B013IVNQ3A, B00YNZKA62, B0798KFQDX, B00DT42TRQ, B07R7VPJJJ |
| $50 gifts for men | baseline_bm25 |  | 0.600 | 0.097 | 1.000 | 0.469 | B08R8SW1NM, B07Y1C853J, B09722KXS8, B07Y1FHHD5, 1726244822 |
| $50 gifts for men | boosted_bm25 | yes | 0.600 | 0.097 | 1.000 | 0.494 | B07Y1C853J, B098MGNSSS, B084SQ8P2P, B07XDGTSFM, B08R8SW1NM |
| $50 gifts for men | enriched_profile |  | 0.400 | 0.065 | 0.500 | 0.327 | B07Z9Q6FHH, B084SQ8P2P, B07ZL13WZP, B07NH2X2YW, B076LVSMM3 |
| $50 not accepted | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07XWNMHWX, B07647ZVMN, B07R762555, B07R636W1D, B00JF3S29Y |
| $50 not accepted | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07P98L6B7, B0897RX562, B0746TG79B, 0967718929, 0985206705 |
| $50 not accepted | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B07RN957Q8, B08DJ4KKFF, B07LCX9RPZ, B00DCK5ZXM, B07R762555 |
| $50 skateboard without waxing music | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| $50 skateboard without waxing music | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | B07PWVJZ8H, 1626252521, B018RSC3X8, B08884YXJQ, B087ZW8STC |
| $50 skateboard without waxing music | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | B08884YXJQ, B07N39GCNB, B087ZW8STC, B07ZKDD1VZ, B07T5RJTT3 |

## Notes

`search_profile` is deterministic ingestion-time text enrichment built from product fields. The `enriched_profile` strategy searches that field plus title/category/brand context.
Metrics are deterministic and use the checked-in judgment list under `data/judgments/product_search_judgments.json`.
