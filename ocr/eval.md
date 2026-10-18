## OCR test on 154 lines it wasn't trained on

| Model | Wrong characters | Lines exactly right |
|---|---|---|
| standard | 349 of 6193 (5.6%) | 42 of 154 |
| current | 440 of 6193 (7.1%) | 28 of 154 |
| mfm | 80 of 6193 (1.3%) | 103 of 154 |
| mfmbest | 77 of 6193 (1.2%) | 103 of 154 |
| current+eng | 157 of 6193 (2.5%) | 83 of 154 |
| mfm+eng | 51 of 6193 (0.8%) | 124 of 154 |
| mfmbest+eng | 50 of 6193 (0.8%) | 123 of 154 |

<details><summary>Every line (standard vs mfmbest+eng)</summary>

| Truth | Standard | mfmbest+eng |
|---|---|---|
| [07:20] mdkrazy : [Ink-and-Wash Painting Name Tag Ring] S>2.5m | [07:20] mdkrazy — : [Ink-and-Wash Painting Name Tag Rinal S>2.5m | [07:20] mdkrazy : [Ink-and-Wash Painting Name Tag Ring] S>2.5m |
| [07:20] HeavySlash : [Black Napoleon] S>Black Napoleon cape -1 | [07:20] HeavySlash ~~: [Black Napoleon] S>Black Napoleon cape -1 | [07:20] HeavySlash : [Black Napoleon] S>Black Napoleon cape -1 |
| [07:20] Ryck : S>Mokbi 180k (3 sets) | [(O?:20]) Ryck 2: S>Mokbi 160k (3 sets) | [07:20] Ryck : S>Mokbi 180k (3 sets) |
| 250 | 250 | 250 |
| [07:28] McLuven : [Dankke] 15k | [O7%:20] McLuvyen : [Dankke] 15k | [07:28] McLuven : [Dankke] 15k |
| [07:28] McLuven : [Dankke] 15k | [07:26] McLuven : [Dankkel] 15k | [07:28] McLuven : [Dankke] 15k |
| [07:08] Kunkkaa : S> GMATK60%250k, cape str60% 250k | [07:06] Kunkkaa :S> GMATK60%250k, cape str60% 250k | [07:06] Kunkkaa : S> GMATK60%250k, cape str60% 250k |
| [07:09] xeDex : [Hearts Tights] S> | [07:09] xeDex : [Hearts Tights] S> | [07:09] xeDex : [Hearts Tights] S> |
| [07:09] HellFire : B>lvl 40 wand and equips as well please. good price :) | [07:09] HellFire :B2lvl 40 wand and equips as well please. good price :) | [07:09] HellFire : B>lvl 40 wand and equips as well please. good price : ) |
| [07:10] Emiko : B>cape 100% int for 40k,S>blue justice cape for 48k | fO7:10]) Emiko +: B>cape 100% int for 40k,S=blue justice cape for 46k | [07:10] Emiko : B>cape 100% int for 40k,S=blue justice cape for 48k |
| [06:54] neg80USD : WTT MY 60% CFA + 60% GFA FOR GFMA 60% | [06:54] neqsOUSD :=WTT MY 60% CFA + 60% GFA FOR GFMA 60% | [06:54] negB0USD :=WTT MY 60% CFA + 60% GFA FOR GFMA 60% |
| [07:36] Pandurtle : S> 10% Gloves Magic Attack Greater | [07:36] Pandurtle :S> 10% Gloves Madqic Attack Greater | [07:36] Pandurtle : S> 10% Gloves Magic Attack Greater |
| [07:36] xeDex : B> Garnet | [07:36]xeDex :B> Garnet | [07:36] xeDex : B> Garnet |
| [07:37] xeDex : So many messages just need 1 for quest at ellinia | f(O7:37]\|xzeDex :So many messages just need 1 for quest at ellinia | [07:37] xeDex : So many messages just need 1 for quest at ellinia |
| [07:37] Lilas : [Steely Throwing Knives] S> Offer / ink wash tag 2.2m | fO7:37]Lilas 4: [Steely Throwing Knives] S> Offer / ink wash tag 2.2m | [07:37] Lilas : [Steely Throwing Knives] S> Offer / ink wash tag 2.2m |
| [18:10] GoldoFunky : SELL BUNNY earmuffs & ORANGE HODDED SHIRT | [16:10] GoldoFunky : SELL BUNNY earmuffs & ORANGE HODDED SHIRT | [18:10] GoldoFunky : SELL BUNNY earmuffs & ORANGE HODDED SHIRT |
| [06:13] Jayee : [Emerald Earrings] S> +3CD earrings 250k | [06:13] Jayee : [Emerald Earrings] S> +3CD earrings 250k | [06:13] Jayee : [Emerald Earrings] S> +3CD earrings 250k |
| [05:55] iBishop : B>overall 10% INT no more then 25k get lost | [05:55] iBishop =: B2averall 10% INT no more then 25k get lost | [05:55] iBishop : B>overall 10% INT no more then 25k get lost |
| [05:55] PaperCutHero : S> SLOTS 40k EA | [05:55] PaperCutHero :S> SLOTS 40kEA | [05:55] PaperCutHero : S> SLOTS 40k EA |
| [05:55] KINGJAMES : SELLING 11 FOUNDER CRATES 280K | [05:55] KINGJAMES : SELLING 11 FOUNDER CRATES 230K | [05:55] KINGJAMES : SELLING 11 FOUNDER CRATES 280K |
| [05:56] Doin : S>SLOTS 40K EACH | [05:56]Doin +: S>SLOTS 40K EACH | [05:56] Doin : S>SLOTS 40K EACH |
| [05:56] serpentine : S> Signature hair coupon! | [05:56]serpentine :S> Siqnature hair coupon! | [05:56] serpentine : S> Siqnature hair coupon! |
| [05:56] ExtraEmily : B>Glass Shoe 50k | [05-56] ExtraEmily :B>Glass Shoe 50k | [05:56] ExtraEmily : B>Glass Shoe 50k |
| [06:27] Briyam : [Emerald Earrings] 8str 2 cd - c/o 900k \| PMO | [06:27] Brivam — : fEmerald Earnings] @str 2 cd - cfo 900k \| PMO | [06:2/] Briyvam : [Emerald Earrings] 8str 2 cd - cfo 9300k \| PMO |
| [06:29] SnailPhD : B>Gloves Magic ATTACK 60% DM price | [06:29] SnailIPhD +: B2Gloves Maqic ATTACK 60% DM price | [06:29] SnailPhD : B>Gloves Magic ATTACK 60% DM price |
| [06:47] Cello : [Processed Wood] B>Processed Wood 400meso each ch5 FM | [06:47]Cello : [Processed Wood] B=Processed Wood 400meso each ch5 FM | [06:47] Cello : [Processed Wood] B>Processed Wood 400meso each ch5 FM |
| [06:47] nachojin : B> Blue Starlight PMO | [06:47] nachoiin :B> Blue Starlight PMO | [06:47] nachojin : B> Blue Starlight PMO |
| [09:33] TeaEgg : S>Critiacal Damage+3 Earring 200K OA LUC 10 30K ea | (09:33) TeaEaq : S>Critiacal Damaqgets Earring 200K OA LUC 10 SOK ea | [09:33] TeaEaq : S>Critiacal Damage+3 Earring 200K OA LUC 10 30K ea |
| [09:33] Meistro : Lol I'll get to each and all of u just 1 at a time please | [09:33] Meistro -:Loll'll getto each and all of u just 1 at atime please | [09:33] Meistro : Lol Ill get to each and all of u just 1 at a time please |
| [09:34] Zenkuro : S> GLOVE ATK 60% ... PM | [09:34] Zenkuro :S> GLOVE ATK 60% ... PM | [09:34] Zenkuro : S> GLOVE ATK 60% ... PM |
| [09:34] joggara : s>earring luk 60%/staff mag 60% | (09:34) jogaqara -: svearring luk 60%0/staff maq 60% | [09:34] joggara : s>earring luk 60%/staff mag 60% |
| [09:34] FujinSama : [Loose Fit Sweater] S> this, bunny earmuffs, slime shirt a | [09:34] FulinSama : Loose Fit Sweater] S> this, bunny earmuffs, slime shirta | [09:34] FujinSama : [Loose Fit Sweater] S> this, bunny earmuffs, slime shirt a |
| nd slips - offer pl0x | nd slios - offer olOx | nd slios - offer pl0x |
| [09:35] Draak : [Great Red Helmet] S> this and GFA 60% offer meso only | (09:35) Draak : [Great Red Helmet] S> this and GFA 60 offer meso only | [09:35] Draak : [Great Red Helmet] S> this and GFA 60% offer meso only |
| [09:35] SasaKi90 : S>FMslot 40k Chnl4Room6Entrance | [09:35] SasakiS0O -: S>FMslot 40k Chni4Roomb6Entrance | [09:35] SasaKi90 : S>FMslot 40k Chnl4Room6Entrance |
| [09:35] Nervous : B> mokbi 150k | (09:35) Nervous -:B> mokbi 150k | [09:35] Nervous : B> mokbi 150k |
| [09:35] Huanghou : [Blue Lutia] C/O is now 380k. Last smega and then ill sell | (09:35) Huanghou °: (Blue Lutal C/O is now 380k. Last smeaa and then ill sell | [09:35] Huanghou : (Blue Lutia] C/O is now 380k. Last smegqa and then ill sell |
| it to highest | it to highest | it to highest |
| [09:35] Kagejin : S> INK AND ASH NAMETAG OFFER | (09:35) Kagelin :S> INK AND ASH NAMETAG OFFER | [09:35] Kagejim : S> INK AND ASH NAMETAG OFFER |
| [09:35] Shadaim : S>+6luck earring PMO | [09:35] Shadaim : S>4+6luck earring PMO | [09:35] Shadaim : S>+6luck earring PMO |
| [09:35] minkyuu : S> ARWEN GLASS SHOE | (09-35) minkvuu °° S> ARWEN GLASS SHOE | [09:35] minkyuu : S> ARWEN GLASS SHOE |
| [09:36] apriori : S>Mystery Crate(11) 290k, Slots 40k, AP/SP Reset 65k | (09:36) apriori +: S>Mystery Crate(11) 290k. Slots 40k, AP/SP Reset 65k | [09:36] apriori : S>Mystery Crate(11) 290k. Slots 40k, AP/SP Reset 65k |
| [09:36] Ganbei : B>EARRING INT 60% PMO (lowest plz) | (09-36) Ganbei -: B>EARRING INT 60% PMO flowest plz} | [09:36] Ganbei : B>EARRING INT 60% PMO flowest plz} |
| [09:36] Profit : S> icicles pmo | (09:36) Profit <:S> icicles oma | [09:36] Profit : S> icicles oma |
| [07:21] KAMIKAZE : B> LIONHEART SWORD + OVERALL LVL 35 WARRIOR | [07:21] KAMIKAZE :B> LIONHEART SWORD + OVERALL LVL 35 WARRIOR | [07:21] KAMIKAZE : B> LIONHEART SWORD + OVERALL LVL 35 WARRIOR |
| [07:21] Kyne : S> SP / AP Reset 90k | [O7:21]Kyne :S>SP/ AP Reset 90k | [07:21] Kyne : S> SP / AP Reset 90k |
| [07:22] HeavySlash : [Black Napoleon] S>Black Napoleon cap -1 cheap | [07:22] HeavySlash — : [Black Napoleon] S=Black Napoleon cap -1 cheap | [07:22] HeavySlash : [Black Napoleon] S>Black Napoleon cap -1 cheap |
| [07:22] shauncho : [Chocolate Chat Ring] S> | [07:22] shauncho : [Chocolate Chat Rina] S> | [07:22] shauncho : [Chocolate Chat Ring] S> |
| [07:13] Snivy : S> emerald 2crit 8 luk, Dagger scroll 60 230k, red whip +2 | [07:13] Snivy =: S> emerald 2crit 6 luk, Daqqer scroll 60 230k, red whip +2 | [07:13] Snivy : S> emerald 2crit 6 luk, Dagger scroll 60 230k, red whip +2 |
| [06:34] Briyam : [Return Scroll - Nearest Town] B>100% Overall Str Scrolls | [06:34] Brivam =: [Retum Scroll - Nearest Town] 6>100% Overall Str Scrolls | [06:34] Briyvam : [Return Scroll - Nearest Town] B>100% Overall Str Scrolls |
| [06:35] Lior : B>Earrings scrolls 60% 80k each! | [06:35] Lior +: ®B>Earrings scrolls 60% 60k each! | [06:35] Lior : B>Earrings scrolls 60% 80k each! |
| [06:35] SnailPhD : B>Gloves for Magic ATT 60% (220k FM CH3) Also B>Glov | [06:35] SnailPhD +: B>Gloves for Magic ATT 60% (220k FM CH3) Also B=Glaov | [06:35] SnailPhD : B>Gloves for Magic ATT 60% (220k FM CH3) Also B>Glov |
| es4int | esdint | es4int |
| [06:20] IceSpike : S<5 Slot. In FM have 5 left. 45k | fO6:20]IceSpike -: S«<5 Slot. In FM have 5 left. 45k | [06:20] IceSpike : S<5 Slot. In FM have 5 left. 45k |
| [06:20] NamiSchwan : buying diamond, sell mith pole arm plus 4 | [06:20] NamiSchwan <: buying diamond, sell mith pole arm plus 4 | [06:20] NamiSchwan : buying diamond, sell mith pole arm plus 4 |
| [06:21] Xiangcai : B> mystery face coupon PMO | [06:21] Xianqcai : B> mystery face coupon PMO | [06:21] Xiangcai : B> mystery face coupon PMO |
| [07:31] Crazypudu : S > earrings DEX 60% 100k | [07:31] Crazypudu :S > earrings DEX 60% 100k | [07:31] Crazypudu : S > earrings DEX 60% 100k |
| %, earr int 60%, two hand axe 60% pmo | 4, earr int 60%, two hand axe 60% pmo | %, earr int 60%, two hand axe 60% pmo |
| S. junk nx 18.5k | S. junk nx 16.5k | S. junk nx 18.5k |
| [07:32] Hitcher : [Mystery Face Coupon] S> Mystery Face Coupon x2 40k ea | [07:32] Hitcher : [Mystery Face Coupon] S> Mystery Face Coupon x2 40k ea | [07:32] Hitcher : [Mystery Face Coupon] S> Mystery Face Coupon x2 40k ea |
| [07:30] Lukotsu : [Bunny Earmuffs] S> 55k | [O¥:30])Lukotsu =: [Bunny Eannuffs] S> 55k | [07:30] Lukotsu : [Bunny Earmuffs] S> 55k |
| [07:30] Lukotsu : [Bunny Ears] S> 60k | [O¥:30]Lukotsu =: [Bunny Ears] S> 60k | [07:30] Lukotsu : [Bunny Ears] S> 60k |
| [07:30] PaperCutHero : S> Mystery Palette | [07:30] PaperCutHero : S> Mystery Palette | [07:30] PaperCutHero : S> Mystery Palette |
| [07:30] OnlyBishop : S>MOKBI 180k 1 ea | [07:30] OnlyBishop -:S>MOKBI 160k 1 ea | [07:30] OnlyBishop : S>MOKBI 180k 1 ea |
| [07:31] Crazypudu : S > earrings DEX 60% 100k | [O¥:31] Crazyoudu :S > earrings DEX 60% 100k | [07:31] Crazypudu : S > earrings DEX 60% 100k |
| bble offer each or both | bble offer each or both | bble offer each or both |
| [05:50] KagonDraka : [Earring DEX Scroll: Intermediate] SELL, SUGEST PRIC | [05:50] KagonDraka — : [Earning DEX Scroll: Intermediate] SELL, SUGEST PRIC | [05:50] KagonDraka : [Earring DEX Scroll: Intermediate] SELL, SUGEST PRIC |
| a | a | a |
| [10:59] Tendency : [Signature Hair Coupon] S> this cause they dont have the | [10:59] Tendency -: [Siqnature Hair Coupon] S> this cause they dont have the | [10:59] Tendency : [Signature Hair Coupon] S> this cause they dont have the |
| cut i want | cut i want | cut i want |
| [11:00] Xdrk : buy red whip offer | [11:00] Xdrk : buy red whip offer | [11:00] Xdrk : buy red whip offer |
| [11:00] jeogun : [Ink-and-Wash Painting Name Tag Ring] S> 1.7m only mesos | (11:00 ieoqun : —nk-and-Wash Painting Name Taga Rina] S> 1.7m only mesos | [11:00] jeoqgun : —nk-and-Wash Painting Name Tag Ring] S> 1.7m only mesos |
| [11:00] jeogun : [Orange Cat Beanie] S> 130k | [11:00] ieoqun : [Orange Cat Beanie] S> 150k | [11:00] jeogun : [Orange Cat Beanie] S> 130k |
| [11:00] Nyght : [Gloves Magic Attack Scroll: Greater] WTS BUYING FLAMING | (11:00) Nvaht : [Gloves Maaic Attack Scroll: Greater] W1S BUYING FLAMING | [11:00] Nyght : [Gloves Magic Attack Scroll: Greater] WTS BUYING FLAMING |
| FEATHERS | FEATHERS | FEATHERS |
| [11:00] arcbite : S> Steely Throwing Knives C/O 5.5m A/W 7m | (11:00) arcbite <: S> Steely Throwing Knives C/O 5.5m AAW 7m | [11:00] arcbite : S> Steely Throwing Knives C/O 5.5m AAW 7/m |
| [11:00] Analytics : T>Black Sunglasses for Bunny ears | [11:00] Analytics <: T>Black Sunglasses for Bunny ears | [11:00] Analytics : T>Black Sunglasses for Bunny ears |
| [11:00] Breadhead : [Dark Shadow Pants] Selling, offer | (11:00) Breadhead -: [Dark Shadow Pants] Selling. offer | [11:00] Breadhead : [Dark Shadow Pants] Selling. offer |
| [11:00] Breadhead : [Fairy Wing] Selling, also have jewels - diamonds etc | [11:00] Breadhead = : [Fairy Wing] Selling, also have jewels - diamonds etc | [11:00] Breadhead : [Fairy Wing] Selling, also have jewels - diamonds etc |
| [11:01] LehemPita : S> K Fan 52 atk PMO | (11:01] LehemPita - S> K Fan 52 atk PMO | [11:01] LehemPita : S> K Fan 52 atk PMO |
| [11:01] Dyle : [Ink-and-Wash Thought Bubble Ring] c/o 800k | [11:01] Dyle <: [—nk-and-Wash Thought Bubble Rina] cfo 800k | [11:01] Dyle : [Ink-and-Wash Thought Bubble Ring] c/o 800k |
| [11:01] Dyle : selling if no higher offer | [11:01] Dvle -: selling if no higher offer | [11:01] Dyle : selling if no higher offer |
| [11:01] Alia : buying trash NX - 18k per! | [11:01] Alia : buying trash NX - 16k per! | [11:01] Alia : buying trash NX - 18k per! |
| [11:02] Amirul : B>Hard Briefcase / S>Earring Luk 60% 125k | 11:07] Amirul <: B>Hard Briefcase / S>Earring Luk 60% 125k | [11:02] Amirul : B>Hard Briefcase / S>Earring Luk 60% 125k |
| [07:08] Jose : B> lvl 30 Black thief hat and hat acc 60% scrolls PM offer | [07:06] Jose :B> lvl 30 Black thief hat and hat acc 60% scrolls PM offer | [07:08] Jose : B> lvl 30 Black thief hat and hat acc 60% scrolls PM offer |
| t | t | t |
| [07:08] Naws : B> Weighted Earrings 4k | [07:08] Naws :B> Weighted Earrings 4k | [07:08] Naws : B> Weighted Earrings 4k |
| [07:08] Kunkkaa : S> GMATK60%250k, cape str60% 250k | [07:08] Kunkkaa :S> GMATK6084250k, cape str60% 250k | [07:08] Kunkkaa : S> GMATK60%250k, cape str60% 250k |
| [07:09] xeDex : [Hearts Tights] S> | [O7:09]xeDex : [Hearts Tiqhts] S> | [07:09] xeDex : [Hearts Tights] S> |
| [06:35] Lior : B>Earrings scrolls 60% 80k each! | [06:35] Lior :B>Earrings scrolls 60% oOk each! | [06:35] Lior : B>Earrings scrolls 60% 80k each! |
| [06:35] SnailPhD : B>Gloves for Magic ATT 60% (220k FM CH3) Also B>Glov | [06:35] SnailPhD :®B>Gloves for Magic ATT 60% (220k FM CH3) Also B=Gloy | [06:35] SnailPhD : B>Gloves for Magic ATT 60% (220k FM CH3) Also B>Gloy |
| es4int | esdint | es4int |
| [06:35] Deasy : B> Kitty Chat Ring 19k | [06:35] Deasy =: B= Kitty Chat Ring 19k | [06:35] Deasy : B> Kitty Chat Ring 19k |
| %, earr int 60%, two hand axe 60% pmo | 4, earr int 60%, two hand axe 60% pmo | %, earr int 60%, two hand axe 60% pmo |
| S. junk nx 18.5k | S. junk nx 136.5k | S. junk nx 18.5k |
| [07:32] Hitcher : [Mystery Face Coupon] S> Mystery Face Coupon x2 40k ea | [07:32] Hitcher =: [Mystery Face Coupon] S> Mystery Face Coupon x2 40k ea | [07:32] Hitcher : [Mystery Face Coupon] S> Mystery Face Coupon x2 40k ea |
| r steelys | r steelys | r steelys |
| [06:06] Cadniumz : WTS Pink Bunny Sweater | [06:06] Cadniumz -:WTS Pink Bunny Sweater | [06:06] Cadniumz : WTS Pink Bunny Sweater |
| [06:07] Rrrafa : S> Pet Equip Speed 100% | [06:07\|]Rrrafa :S> Pet Equip Speed 100% | [06:07] Rrrafa : S> Pet Equip Speed 100% |
| [07:23] Hakushu : b | [07:23] Hakushu <:b | [07:23] Hakushu : b |
| [07:23] BaldQT : TUV | [07:23] BaldOT :TUV | [07:23] BaldQOT : TUV |
| [07:24] PaperCutHero : S> SLOTS 40k EA S> Kitty Chat Ring S> Slimt T shirt | [07:24] PaperCutHero :S> SLOTS 40k EA S> Kitty Chat Ring S> Slimt T shirt | [07:24] PaperCutHero : S> SLOTS 40k EA S> Kitty Chat Ring S> Slimt T shirt |
| C/os 900k also 44 founders chests | Cfos 900k also 44 founders chests | C/os 900k also 44 founders chests |
| [06:49] Quote : S>Armor Crafting Catalyst for 45k | [06:49] Quote : S>Armor Crafting Catalyst for 45k | [06:49] Quote : S>Armor Crafting Catalyst for 45k |
| [06:49] wantdefu : [Green Icarus Cape] S>LUK+3 SLOT 4/Gloves Dagger atk | [06:49] wantdefu -: [Green Icarus Cape] S=LUK+3 SLOT 4/Gloves Daqaer atk | [06:49] wantdefu : [Green Icarus Cape] S>LUK+3 SLOT 4/Gloves Dagger atk |
| LZ <3 | LZ <3 | LZ <3 |
| [07:26] NekoRamen : B> 2 x Cape 100% LUK Please | [07:26] NekoRamen :6B> 2x Cape 100% LUK Please | [07:26] NekoRamen : B> 2 x Cape 100% LUK Please |
| LZ <3 | LZ <3 | LZ <3 |
| [07:26] NekoRamen : B> 2 x Cape 100% LUK Please | [07:26] NekoRamen :B> 2x Cape 100% LUK Please | [07:26] NekoRamen : B> 2 x Cape 100% LUK Please |
| 250 | 250 | 250 |
| [07:34] Melic : B>KUMBI 350-400k Buying 5 sets singles or bundle | [07:34] Melic :B>KUMBI 350-400k Buying 5 sets singles or bundle | [07:34] Melic : B>KUMBI 350-400k Buying 5 sets singles or bundle |
| sell text me | sell text me | sell text me |
| [06:48] Azerl : S>Gloves ATT Scroll 680K, Kumbi Star 500K | [06:46] Azerl -:S>Gloves ATT Scroll 660K, Kumbi Star 500K | [06:48] Azerl : S>Gloves ATT Scroll 660K, Kumbi Star 500K |
| [06:26] DaggerStan : B> +3 KFan, S> AVG KFan, send offers | [06:26] DaqgerStan :B>+3KEFan, S> AVG KFan, send offers | [06:26] DaggerStan : B> +3 KFan, S> AVG KFan, send offers |
| [07:37] xeDex : So many messages just need 1 for quest at ellinia | fO7:37\|xeDex <: So many messaqes just need 1 for quest at ellinia | [07:37] xeDex : So many messages just need 1 for quest at ellinia |
| [07:37] Lilas : [Steely Throwing Knives] S> Offer / ink wash tag 2.2m | [07:37] Lilas : [Steely Throwing Knives] S> Offer / ink wash taq 2.2m | [07:37] Lilas : [Steely Throwing Knives] S> Offer / ink wash tag 2.2m |
| [07:38] shauncho : [White Label Ring] S> c/o 170k by Steal | [07:38] shauncho ~— : (White Label Rina] S> c/o 170k by Steal | [07:38] shauncho : [White Label Ring] S> c/o 170k by Steal |
| 129k ch.15 FM | 129k ch.15 FM | 129k ch.15 FM |
| 89k ch.15 FM | o9k ch.15 FM | 839k ch.15 FM |
| [06:49] Gimple : S > +3 BAZLUD (45 DAGGER) \|\| PMO | [06:49] Gimple :S > +43 BAZLUD (45 DAGGER} \|\| PMO | [06:49] Gimple : S > +3 BAZLUD (45 DAGGER} \|\| PMO |
| [06:49] Quote : S>Armor Crafting Catalyst for 45k | [06:49] Quote : S>Armor Crafting Catalyst for 45k | [06:49] Quote : S>Armor Crafting Catalyst for 45k |
| [06:54] neg80USD : WTT MY 60% CFA + 60% GFA FOR GFMA 60% | [06:54] neqsOUSD :=WTT MY 60% CFA + 60% GFA FOR GFMA 60% | [06:54] negB0USD : WT I MY 60% CFA + 60% GFA FOR GFMA 60% |
| [06:54] Invy : [Selective 5-slot Coupon] S>40k | [06:54] Invy — : [Selective 5-slot Coupon] S$>40k | [06:54] Invy : [Selective 5-slot Coupon] S>40k |
| [06:55] Cartier : [Yellow Square] S> +2 INT earrings 4 upgrades left send offe | [06:55] Cartier : Yellow Square] S> +2 INT earrings 4 uparades left send offe | [06:55] Cartier : [Yellow Square] S> +2 INT earrings 4 upgrades left send offe |
| Yellow Square | Yellow Square | Yellow Square |
| Bunny Ears | Bunny Ears | Bunny Ears |
| 1 for 25,000 mesos | 1 for 26 {HH} mesos | 1 for 25,HH} mesos |
| Angel Wand | Angel Wand | Angel Wand |
| Cherub's Bow | Cherub's Bow | Cherub's Bow |
| 1 for 120,000 mesos | 1 for 120,000 mesos | 1 for 120,000 mesos |
| 1 for 120,000 mesos | 1 for 120,000 mesos | 1 for 120,000 mesos |
| 1 for 120,000 mesos | 1 for 120,000 mesos | 1 for 120,000 mesos |
| Earring STR Scroll: Inter... | Earring STR Scroll: Inter... | Earring STR Scroll: Inter... |
| 1 for 120,000 mesos | 1 for 120,000 mesos | 1 for 120,000 mesos |
| Cutlus | Cutlus | Cutlus |
| Cape STR Scroll: Lesser | Cape STR Scroll: Lesser | Cape STR Scroll: Lesser |
| Blank Eye Patch | Blank Eye Patch \| | Blank Eye Patch \| |
| 1 for 239,999 mesos | 1 for 239,999 mesos \| | 1 for 239,999 mesos \| |
| Angel Wand | Angel Wand | Angel Wand |
| 1 for 45,999 mesos | 1 for 46,9949 mesos | 1 for 45,999 mesos |
| Overall Armor STR Scroll:... | Overall Armor STR Scroll:... | Overall Armor STR Scroll:... |
| Pink Allstar | Pink Allstar \| | Pink Allstar \| |
| 1 for 8,888 mesos | l fore ,ce8 mesos | 1 for 2,888 mesos |
| Angel Wand | Angel Wand | Angel Wand |
| 1 for 515,000 mesos | 1 for 515,000 mesos | 1 for 515,000 mesos |
| Kitty Chat Ring | Kitty Chat Ring | Kitty Chat Ring |
| Kitty Chat Ring | Kitty Chat Ring | Kitty Chat Ring |
| 1 for 21,999 mesos | 1 for 21,9949 mesos | 1 for 21,999 mesos |
| Baby Angel Wings | Baby Angel Wings | Baby Angel Wings |
| Gold Kitty Slippers | Gold Kitty Slippers \| | Gold Kitty Slippers \| |
| Kitty Chat Ring | Kitty Chat Ring | Kitty Chat Ring |
| 1 for 39,500 mesos | 1 for 39,500 mesos | 1 for 39,500 mesos |
| 1 for 39,500 mesos | 1 for 39,500 mesos | 1 for 39,500 mesos |
| Gold Kitty Slippers | Gold Kitty Slippers | Gold Kitty Slippers |

</details>
