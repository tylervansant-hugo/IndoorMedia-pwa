#!/usr/bin/env python3
"""Parse Zone 7 B2 2026 renewals PDF data into pending_renewals.json"""

import json
import re
import os

# Raw data extracted from the PDF
RAW_DATA = [
    {"zone":"07W","store":"ALB07W-3367","rep":"Dennis Stachura","status":"Active","business":"Vitality Medical","account":"WJ354582","contract":"J416657E","contractPrice":"$2,790.00","cycleRevenue":"$1,333.00","lateBalance":"$-","contactName":"Melissa Fuller","phone":"4068552422","email":"vitalitymedical406@gmail.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"5317 Grand Ave","city":"Billings","state":"MT","zip":"59106","category":"Medical","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07W","store":"ALB07W-0243","rep":"Joanna Finnegan","status":"Active","business":"Tire Rama","account":"J418984E","contract":"J418984E","contractPrice":"$1,252.70","cycleRevenue":"$1,128.00","lateBalance":"$-","contactName":"Jimmy Le Blanc","phone":"2087657777","email":"Jimmy.leblanc@tirerama.com","phone2":"","start":"2/1/2026","end":"5/1/2026","runLength":"1","address":"220 Ironwood Dr","city":"Coeur D'Alene","state":"ID","zip":"83814","category":"Repair / Body / Maintenance","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07W","store":"YOK07W-0020","rep":"Lisa Castic","status":"Active","business":"Rosa's Pizza","account":"WJ253432","contract":"J405115E","contractPrice":"$2,475.00","cycleRevenue":"$619.00","lateBalance":"$-","contactName":"Syrie Barsness","phone":"5092355678","email":"syriebarsness@gmail.com","phone2":"5097102443","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"4 Cheney Spokane Rd","city":"Cheney","state":"WA","zip":"99004","category":"Pizza","adSize":"Single","exclusive":"FALSE","renewal":"J427006E"},
    {"zone":"07W","store":"FIF07W-0002","rep":"Lorin R. Clark","status":"Active","business":"Stokes Burger Ranch","account":"WA6927","contract":"J329350","contractPrice":"$7,600.00","cycleRevenue":"$981.00","lateBalance":"$-","contactName":"David Stokes","phone":"5098373003","email":"stokesburgerranch@gmail.com","phone2":"5098432601","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"2010 YAKIMA VALLEY HWY","city":"Sunnyside","state":"WA","zip":"98944","category":"Casual Dining","adSize":"Single","exclusive":"FALSE","renewal":"J420082E"},
    {"zone":"07W","store":"ALB07W-4025","rep":"Richard Diamond","status":"Active","business":"Montana Advanced Caregivers","account":"J406206E","contract":"J406206E","contractPrice":"$19,534.95","cycleRevenue":"$1,511.00","lateBalance":"$-","contactName":"Richard Abromeit","phone":"4066987242","email":"montanaadvancedcaregivers@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"611 N 27th St","city":"Billings","state":"MT","zip":"59101","category":"Dispensary","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07W","store":"ALB07W-1227","rep":"Richard Diamond","status":"Active","business":"Montana Advanced Caregivers","account":"J406206E","contract":"J406206E","contractPrice":"$19,534.95","cycleRevenue":"$1,686.00","lateBalance":"$-","contactName":"Richard Abromeit","phone":"4066987242","email":"montanaadvancedcaregivers@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"670 Main St.","city":"Billings","state":"MT","zip":"59105","category":"Dispensary","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07W","store":"ALB07W-0630","rep":"Richard Diamond","status":"Active","business":"Montana Advanced Caregivers","account":"J406206E","contract":"J406206E","contractPrice":"$19,534.95","cycleRevenue":"$1,686.00","lateBalance":"$-","contactName":"Richard Abromeit","phone":"4066987242","email":"montanaadvancedcaregivers@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"2334 Central Ave","city":"Billings","state":"MT","zip":"59102","category":"Dispensary","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07W","store":"ALB07W-4041","rep":"Tyler VanSant","status":"Active","business":"Banano Smoothies/Spinners Frozen Yogurt","account":"SJ357100","contract":"J407143E","contractPrice":"$4,316.00","cycleRevenue":"$1,079.00","lateBalance":"$-","contactName":"Dave Diehl","phone":"2085630002","email":"dave@bottleshopmt.com","phone2":"4066903276","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"3137 Grand Ave","city":"Billings","state":"MT","zip":"59102","category":"Ice Cream / Yogurt Shops","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-1978","rep":"Fabian Reyes","status":"Active","business":"Oscar Nail Spa","account":"WJ114306","contract":"J403369E","contractPrice":"$7,560.00","cycleRevenue":"$1,890.00","lateBalance":"$-","contactName":"Hoang Pham","phone":"3606884485","email":"Hoangpham10@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"2637 North Pearl Street","city":"Tacoma","state":"WA","zip":"98407","category":"Hair / Nails / Spa / Tanning","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-0186","rep":"Kale Lundberg","status":"Active","business":"Tres Compadres Taqueria","account":"J404789E","contract":"J404789E","contractPrice":"$3,081.33","cycleRevenue":"$770.00","lateBalance":"$-","contactName":"Roberto Garcia","phone":"3602043042","email":"rogar56garcia@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"8196 NE STATE HIGHWAY 104","city":"Kingston","state":"WA","zip":"98346","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"FME07X-0171","rep":"Kale Lundberg","status":"Active","business":"Liberty Tax","account":"J419210E","contract":"J419210E","contractPrice":"$4,084.55","cycleRevenue":"$1,241.00","lateBalance":"$-","contactName":"Suzanne Zimmerman","phone":"3603771040","email":"suzanne.zimmerman@libtax.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"5050 State Highway 303 Northeast","city":"Bremerton","state":"WA","zip":"98311-3687","category":"Financial","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-1524","rep":"Kale Lundberg","status":"Active","business":"Liberty Tax","account":"J419210E","contract":"J419210E","contractPrice":"$4,084.55","cycleRevenue":"$802.00","lateBalance":"$-","contactName":"Suzanne Zimmerman","phone":"3603771040","email":"suzanne.zimmerman@libtax.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"1401 N.E. McWilliams","city":"Bremerton","state":"WA","zip":"98311","category":"Financial","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"QFC07X-0872","rep":"Mathew Hayward","status":"Inactive","business":"Vai Hydration Lounge","account":"WJ363176","contract":"J363176","contractPrice":"$3,125.00","cycleRevenue":"$781.00","lateBalance":"$-","contactName":"Loretta Axtell","phone":"4253597572","email":"info@vaidration.com","phone2":"4255352917","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"9999 Holman Road Northwest","city":"Seattle","state":"WA","zip":"98117","category":"Medical","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"QFC07X-0835","rep":"Mathew Hayward","status":"Inactive","business":"Santa Fe Mexican Grill","account":"WJ362544","contract":"J407092E","contractPrice":"$3,125.04","cycleRevenue":"$781.00","lateBalance":"$-","contactName":"Ricky Bobadilla","phone":"4252457916","email":"ricky@santafemex.com","phone2":"2063272046","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"7500 B 196Th Southwest","city":"Lynnwood","state":"WA","zip":"98036","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-1472","rep":"Richard Diamond","status":"Active","business":"Roundtable Pizza","account":"J407007E","contract":"J407007E","contractPrice":"$5,250.00","cycleRevenue":"$1,313.00","lateBalance":"$-","contactName":"Amrit Grewal","phone":"3604247979","email":"amritveer.singh@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"315 E College Way","city":"Mount Vernon","state":"WA","zip":"98273","category":"Pizza","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-1461","rep":"Richard Diamond","status":"Active","business":"Fresa Mexican Kitchen & Tequila Bar","account":"J412512E","contract":"J412512E","contractPrice":"$8,800.00","cycleRevenue":"$1,792.00","lateBalance":"$-","contactName":"Mario Gomez","phone":"4253501636","email":"mgmariogomez3@gmail.com","phone2":"","start":"8/1/2025","end":"5/1/2026","runLength":"3","address":"520 128th St SW","city":"Everett","state":"WA","zip":"98204","category":"Mexican","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"QFC07X-0827","rep":"Richard Diamond","status":"Active","business":"See Fah Thai","account":"WJ352228","contract":"J405746E","contractPrice":"$4,174.92","cycleRevenue":"$1,044.00","lateBalance":"$-","contactName":"Chun Sung Wu","phone":"4252078630","email":"seefah.thai@outlook.com","phone2":"2062912054","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"6940 Coal Creek Pkwy SE","city":"Newcastle","state":"WA","zip":"98059","category":"Asian","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-1885","rep":"Richard Diamond","status":"Active","business":"The Golden Olive","account":"WJ352213","contract":"J408051E","contractPrice":"$3,000.00","cycleRevenue":"$750.00","lateBalance":"$-","contactName":"Khaled Ajez","phone":"2062164674","email":"thegoldenolivellc@gmail.com","phone2":"2063836404","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"516 1st Avenue West","city":"Seattle","state":"WA","zip":"98119","category":"Cultural Dining","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"FME07X-0031","rep":"Richard Diamond","status":"Active","business":"Dairy Queen","account":"J414658E","contract":"J414658E","contractPrice":"$2,275.00","cycleRevenue":"$1,075.00","lateBalance":"$-","contactName":"Reece Sangha","phone":"2065789000","email":"dqrentonbenson@gmail.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"17801 108th Ave SE","city":"Renton","state":"WA","zip":"98055","category":"Ice Cream / Yogurt Shops","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07X","store":"SAF07X-4406","rep":"Lisa - William Flerry","status":"Inactive","business":"Up Wellness Spa","account":"C008932","contract":"J407791E","contractPrice":"$4,800.00","cycleRevenue":"$1,200.00","lateBalance":"$-","contactName":"Delisha Johnson","phone":"2532129992","email":"upwellnessspa7307@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"11330 N W 51st Ave","city":"Gig Harbor","state":"WA","zip":"98332","category":"Beauty & Health","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"SAF07Y-1601","rep":"Amy Dixon","status":"Active","business":"Top Shelf Cannabis","account":"WJ288481","contract":"J405914E","contractPrice":"$12,993.00","cycleRevenue":"$1,646.00","lateBalance":"$-","contactName":"Brian Stacy","phone":"5034722405","email":"brian@topshelfmcminnville.com","phone2":"9712416624","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"2490 NE HIGHWAY 99W","city":"McMinnville","state":"OR","zip":"97128","category":"Dispensary","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"SAF07Y-1601","rep":"Amy Dixon","status":"Active","business":"CLRM V dba Five Guys","account":"J402883E","contract":"J402883E","contractPrice":"$8,496.20","cycleRevenue":"$1,088.00","lateBalance":"$-","contactName":"Ryan Coady","phone":"4804044886","email":"Wendi@or5g.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"2490 NE HIGHWAY 99W","city":"McMinnville","state":"OR","zip":"97128","category":"Casual Dining","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"SAF07Y-2623","rep":"Anthony Marty Eng","status":"Active","business":"Just Pho You","account":"J405924E","contract":"J405924E","contractPrice":"$3,487.00","cycleRevenue":"$872.00","lateBalance":"$-","contactName":"Trang Tran","phone":"5039620181","email":"Trangptran2003@yahoo.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"1140 North Springbrook Road","city":"Newberg","state":"OR","zip":"97132","category":"Asian","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"SAF07Y-2623","rep":"Anthony Marty Eng","status":"Active","business":"La Sierra Mexican Restaurant & Cantina","account":"W0191","contract":"J406675E","contractPrice":"$6,304.80","cycleRevenue":"$976.00","lateBalance":"$-","contactName":"Rigo Lopez","phone":"5034876458","email":"lasierranewberg@gmail.com","phone2":"5033325267","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"1140 North Springbrook Road","city":"Newberg","state":"OR","zip":"97132","category":"Mexican","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"SAF07Y-0591","rep":"Anthony Marty Eng","status":"Active","business":"Isse Salon","account":"WJ68716","contract":"J407414E","contractPrice":"$4,498.44","cycleRevenue":"$1,125.00","lateBalance":"$-","contactName":"Thuy Khong","phone":"5036936797","email":"Thuykhong@yahoo.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"888 N.E. 25th Ave","city":"Hillsboro","state":"OR","zip":"97124","category":"Hair / Nails / Spa / Tanning","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"SAF07Y-2623","rep":"Anthony Marty Eng","status":"Active","business":"Momiji Sushi & Bento","account":"J406443E","contract":"J406443E","contractPrice":"$2,844.00","cycleRevenue":"$711.00","lateBalance":"$-","contactName":"Rachel Zhang","phone":"5038533125","email":"Momijinewberg@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"1140 North Springbrook Road","city":"Newberg","state":"OR","zip":"97132","category":"Cultural Dining","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"ALB07Y-3593","rep":"Kenneth Abbay","status":"Active","business":"Kanopy 7","account":"WJ358586","contract":"J358586","contractPrice":"$4,536.00","cycleRevenue":"$1,134.00","lateBalance":"$-","contactName":"Dave Uribe","phone":"5416019667","email":"dave@kanopy7.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"113 Ross Lane","city":"Medford","state":"OR","zip":"97501","category":"Dispensary","adSize":"Double","exclusive":"FALSE","renewal":"J418640E"},
    {"zone":"07Y","store":"SAF07Y-1666","rep":"Kenneth Abbay","status":"Active","business":"Los Dos Amigos Fiesta","account":"WJ358595","contract":"J358595","contractPrice":"$3,645.00","cycleRevenue":"$911.00","lateBalance":"$607.50","contactName":"Coco Anaya","phone":"5419570409","email":"anayacoco64@gmail.com","phone2":"5415802800","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"1539 NE Stephens St.","city":"Roseburg","state":"OR","zip":"97470","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"ALB07Y-0577","rep":"Kenneth Abbay","status":"Active","business":"Allstate Toni L. Bonner","account":"WJ358598","contract":"J358598","contractPrice":"$2,555.00","cycleRevenue":"$639.00","lateBalance":"$-","contactName":"Toni L. Bonner","phone":"5418833641","email":"tonibonner@allstate.com","phone2":"5412813641","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"5500 S 6th St","city":"Klamath Falls","state":"OR","zip":"97603","category":"Insurance","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Y","store":"FME07Y-0035","rep":"Richard Leibowitz","status":"Active","business":"Big 5 Sporting Goods","account":"CJ129746","contract":"J401057E","contractPrice":"$83,500.00","cycleRevenue":"$835.00","lateBalance":"$13,360.03","contactName":"Peter Mulvaney","phone":"3105360611","email":"pcm@big5corp.com","phone2":"7023951474","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"11425 SW Beaverton Hillsdale Hwy","city":"Beaverton","state":"OR","zip":"97005-3050","category":"Sporting / Military Goods & Supplies","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"ALB07Z-3417","rep":"Austin Dewitt","status":"Inactive","business":"Twister Donuts","account":"J414920E","contract":"J414920E","contractPrice":"$1,962.50","cycleRevenue":"$981.00","lateBalance":"$-","contactName":"Lorenzo Duarte","phone":"3604518568","email":"Lorenzoduarte0810@gmail.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"3520 Pacific Ave S E","city":"Olympia","state":"WA","zip":"98501","category":"Donut Shops","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"FME07Z-0127","rep":"Catalina Zinzu Garcia","status":"Inactive","business":"Agave Azul","account":"J403733E","contract":"J403733E","contractPrice":"$4,268.00","cycleRevenue":"$1,067.00","lateBalance":"$-","contactName":"Angel Santana","phone":"5036780654","email":"agaveazul2024@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"2497 SE Burnside Rd","city":"Gresham","state":"OR","zip":"97080-1299","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"ALB07Z-0564","rep":"Catalina Zinzu Garcia","status":"Inactive","business":"La Michoacana Dulce","account":"J405246E","contract":"J405246E","contractPrice":"$3,036.50","cycleRevenue":"$759.00","lateBalance":"$-","contactName":"Estera Bircea","phone":"9714019778","email":"birceaestera@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"451 NE 181st Ave","city":"Portland","state":"OR","zip":"97230","category":"Ice Cream / Yogurt Shops","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"FME07Z-0125","rep":"Dave Boring","status":"Active","business":"Muchas Gracias Mexican Food","account":"J406958E","contract":"J406958E","contractPrice":"$4,086.00","cycleRevenue":"$1,022.00","lateBalance":"$-","contactName":"Fernando Garcia","phone":"9713832727","email":"garferjr.mg@gmail.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"6615 NE Glisan St","city":"Portland","state":"OR","zip":"97213-5068","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"FME07Z-0460","rep":"Dave Boring","status":"Active","business":"Muchas Gracias, Salmon Creek, WA","account":"WJ217158","contract":"J408208E","contractPrice":"$10,926.00","cycleRevenue":"$1,172.00","lateBalance":"$-","contactName":"Martin Gonzalez","phone":"3605732125","email":"Odaliz1leilany@icloud.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"800 NE Tenney Rd","city":"Vancouver","state":"WA","zip":"98685","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1842","rep":"Dave Boring","status":"Active","business":"Muchas Gracias, Salmon Creek, WA","account":"WJ217158","contract":"J408208E","contractPrice":"$10,926.00","cycleRevenue":"$780.00","lateBalance":"$-","contactName":"Martin Gonzalez","phone":"3605732125","email":"Odaliz1leilany@icloud.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"13023 NE Hwy 99","city":"Vancouver","state":"WA","zip":"98686","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"ALB07Z-0580","rep":"Dave Boring","status":"Active","business":"Muchas Gracias, Salmon Creek, WA","account":"WJ217158","contract":"J408208E","contractPrice":"$10,926.00","cycleRevenue":"$780.00","lateBalance":"$-","contactName":"Martin Gonzalez","phone":"3605732125","email":"Odaliz1leilany@icloud.com","phone2":"","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"14300 NE 20th Ave","city":"Vancouver","state":"WA","zip":"98686","category":"Mexican","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1436","rep":"Fabian Reyes","status":"Active","business":"Secret Burger Kitchen","account":"J401779E","contract":"J401779E","contractPrice":"$4,700.00","cycleRevenue":"$1,175.00","lateBalance":"$-","contactName":"Paul Sandhu","phone":"2535078653","email":"Shayna@hitacoma.com","phone2":"","start":"2/1/2025","end":"5/1/2026","runLength":"4","address":"1624 72nd St E","city":"Tacoma","state":"WA","zip":"98404","category":"Casual Dining","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1645","rep":"Fabian Reyes","status":"Active","business":"D&S Autocare","account":"J417778E","contract":"J417778E","contractPrice":"$2,200.00","cycleRevenue":"$1,100.00","lateBalance":"$-","contactName":"David Runkel","phone":"2535277331","email":"Davidjr.dsac@gmail.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"10223 Gravelly Lake Dr SW","city":"Lakewood","state":"WA","zip":"98499","category":"Accessories / Parts","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1231","rep":"Jan Banks","status":"Active","business":"Apollo Plumbing, Heating & Air Conditioning","account":"J402722E","contract":"J424079E","contractPrice":"$-","cycleRevenue":"$-","lateBalance":"$-","contactName":"Isabeau Kennedy","phone":"5032601604","email":"isabeau@apolloservices.com","phone2":"","start":"2/1/2026","end":"5/1/2026","runLength":"1","address":"12032 SE Sunnyside Rd","city":"Clackamas","state":"OR","zip":"97015","category":"Home Improvement / Contracting / Supplies","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1436","rep":"Kale Lundberg","status":"Active","business":"Anglea's Restaurant","account":"WJ372682","contract":"J372682","contractPrice":"$5,602.50","cycleRevenue":"$1,401.00","lateBalance":"$-","contactName":"Teresa Maycumber","phone":"2535319329","email":"angleascatering1@gmail.com","phone2":"2533810805","start":"5/1/2025","end":"5/1/2026","runLength":"4","address":"1624 72nd St E","city":"Tacoma","state":"WA","zip":"98404","category":"Casual Dining","adSize":"Double","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"QFC07Z-0105","rep":"Kale Lundberg","status":"Active","business":"Emerald City Smoothie","account":"J416903E","contract":"J416903E","contractPrice":"$1,245.00","cycleRevenue":"$623.00","lateBalance":"$-","contactName":"Almand Newton","phone":"2533590903","email":"ahmadn253ecs@gmail.com","phone2":"","start":"11/1/2025","end":"5/1/2026","runLength":"2","address":"11104 Pacific Ave S","city":"Tacoma","state":"WA","zip":"98444","category":"Fitness & Health","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1436","rep":"Kale Lundberg","status":"Active","business":"Liberty Tax","account":"J421199E","contract":"J421199E","contractPrice":"$2,935.59","cycleRevenue":"$1,046.00","lateBalance":"$-","contactName":"Tracey Morris","phone":"3609997978","email":"tracy.morris@libtax.com","phone2":"","start":"2/1/2026","end":"5/1/2026","runLength":"1","address":"1624 72nd St E","city":"Tacoma","state":"WA","zip":"98404","category":"Financial","adSize":"Single","exclusive":"FALSE","renewal":""},
    {"zone":"07Z","store":"SAF07Z-1437","rep":"Kale Lundberg","status":"Active","business":"Liberty Tax","account":"J421199E","contract":"J421199E","contractPrice":"$2,935.59","cycleRevenue":"$775.00","lateBalance":"$-","contactName":"Tracey Morris","phone":"3609997978","email":"tracy.morris@libtax.com","phone2":"","start":"2/1/2026","end":"5/1/2026","runLength":"1","address":"1302 S 38th St","city":"Tacoma","state":"WA","zip":"98418","category":"Financial","adSize":"Single","exclusive":"FALSE","renewal":""},
]

# Also the DigitalBoost renewal from the second table in the PDF
DIGITAL_DATA = [
    {"zone":"07Y","rep":"Anthony Marty Eng","status":"Active","business":"La Sierra Mexican Restaurant & Cantina","account":"W0191","contract":"J406675E","contractPrice":"$6,304.80","lateBalance":"$-","contactName":"Rigo Lopez","phone":"5034876458","email":"lasierranewberg@gmail.com","phone2":"5033325267","start":"5/1/2025","end":"5/1/2026","runLength":"12","impressions":"30K","product":"DigitalBoost"},
]

def clean_price(p):
    if not p or p == '$-' or p == '$ -':
        return 0
    return float(p.replace('$', '').replace(',', '').replace(' ', '').strip() or '0')

def format_phone(p):
    if not p:
        return ''
    p = re.sub(r'[^\d]', '', str(p))
    if len(p) == 10:
        return f"({p[:3]}) {p[3:6]}-{p[6:]}"
    return p

def main():
    output_path = os.path.join(os.path.dirname(__file__), '..', 'pwa', 'public', 'data', 'pending_renewals.json')
    
    renewals = []
    for r in RAW_DATA:
        renewal = {
            "zone": r["zone"],
            "store": r["store"],
            "rep": r["rep"],
            "repStatus": r["status"],
            "business": r["business"],
            "accountNumber": r["account"],
            "contractNumber": r["contract"],
            "contractPrice": clean_price(r["contractPrice"]),
            "cycleRevenue": clean_price(r["cycleRevenue"]),
            "lateBalance": clean_price(r["lateBalance"]),
            "contactName": r["contactName"],
            "phone": format_phone(r["phone"]),
            "email": r["email"],
            "phone2": format_phone(r["phone2"]),
            "startDate": r["start"],
            "endDate": r["end"],
            "runLength": r["runLength"],
            "address": r["address"],
            "city": r["city"],
            "state": r["state"],
            "zip": r["zip"],
            "category": r["category"],
            "adSize": r["adSize"],
            "exclusive": r["exclusive"] == "TRUE",
            "renewalContract": r.get("renewal", ""),
            "cycle": "B2",
            "product": "Register Tape",
        }
        renewals.append(renewal)
    
    # Add digital renewals
    for r in DIGITAL_DATA:
        renewal = {
            "zone": r["zone"],
            "store": "",
            "rep": r["rep"],
            "repStatus": r["status"],
            "business": r["business"],
            "accountNumber": r["account"],
            "contractNumber": r["contract"],
            "contractPrice": clean_price(r["contractPrice"]),
            "cycleRevenue": 0,
            "lateBalance": clean_price(r["lateBalance"]),
            "contactName": r["contactName"],
            "phone": format_phone(r["phone"]),
            "email": r["email"],
            "phone2": format_phone(r["phone2"]),
            "startDate": r["start"],
            "endDate": r["end"],
            "runLength": r["runLength"],
            "address": "",
            "city": "",
            "state": "",
            "zip": "",
            "category": "",
            "adSize": "",
            "exclusive": False,
            "renewalContract": "",
            "cycle": "B2",
            "product": r.get("product", "DigitalBoost"),
            "impressions": r.get("impressions", ""),
        }
        renewals.append(renewal)
    
    with open(output_path, 'w') as f:
        json.dump(renewals, f, indent=2)
    
    # Stats
    from collections import Counter
    reps = Counter(r['rep'] for r in renewals)
    zones = Counter(r['zone'] for r in renewals)
    total_value = sum(r['cycleRevenue'] for r in renewals)
    
    print(f"Total renewals: {len(renewals)}")
    print(f"Total cycle revenue: ${total_value:,.2f}")
    print(f"\nBy zone: {dict(zones)}")
    print(f"\nBy rep:")
    for rep, count in reps.most_common():
        print(f"  {rep}: {count}")

if __name__ == "__main__":
    main()
