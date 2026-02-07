# Knowledge base with keyword-matching RAG retrieval (in-memory, no external deps)
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeEntry:
  """A single knowledge article."""

  title: str
  category: str  # visa / tips / culture / safety / transport / food
  destination: str  # target destination, or "general"
  content: str
  keywords: List[str] = field(default_factory=list)


# ------------------------------------------------------------------ #
# Built-in knowledge entries (20+)
# ------------------------------------------------------------------ #

_BUILTIN_ENTRIES: List[KnowledgeEntry] = [
  # === Japan - Visa ===
  KnowledgeEntry(
    title="日本签证政策（中国公民）",
    category="visa",
    destination="日本",
    content=(
      "中国公民前往日本需要办理签证。常见类型：\n"
      "1. 单次旅游签证：有效期3个月，停留15天。需提供在职证明、银行流水（年收入10万+）、行程单。\n"
      "2. 三年多次签证：首次须包含冲绳或东北六县住宿。年收入20万+或有足够资产证明。\n"
      "3. 五年多次签证：年收入50万+。\n"
      "办理周期：5-7个工作日。须通过指定旅行社代办，不接受个人直接申请。\n"
      "免签条件：持有美国、加拿大、澳洲等有效签证可申请72小时过境免签（限特定口岸）。"
    ),
    keywords=["日本", "签证", "visa", "办签", "免签", "多次签", "旅游签"],
  ),

  # === Japan - Transport ===
  KnowledgeEntry(
    title="日本交通IC卡指南",
    category="transport",
    destination="日本",
    content=(
      "日本主要IC交通卡：\n"
      "1. Suica（西瓜卡）：JR东日本发行，东京地区最常用。\n"
      "2. PASMO：关东地区私铁/地铁通用。\n"
      "3. ICOCA：JR西日本发行，关西地区最常用。\n"
      "这些卡全国通用，可刷便利店、自动贩卖机。\n"
      "购买：车站自动售票机，押金500日元。\n"
      "充值：售票机或便利店。\n"
      "注意：2023年起Suica实体卡暂停发售，建议使用iPhone/Apple Watch的Suica功能。\n"
      "推荐JR Pass：如果行程跨城市，购买JR Pass（7/14/21天）会更划算。"
    ),
    keywords=["日本", "交通", "IC卡", "Suica", "西瓜卡", "PASMO", "ICOCA", "JR Pass", "地铁"],
  ),

  # === Japan - Culture ===
  KnowledgeEntry(
    title="日本礼仪与文化禁忌",
    category="culture",
    destination="日本",
    content=(
      "日本旅行礼仪须知：\n"
      "1. 公共场所保持安静，电车上请将手机调为静音模式。\n"
      "2. 不要边走边吃（部分景区除外）。\n"
      "3. 垃圾需带走，街上垃圾桶很少。分类丢弃：可燃/不可燃/瓶罐/纸类。\n"
      "4. 进入室内（部分餐厅、寺庙、民宿）需脱鞋。\n"
      "5. 筷子禁忌：不要将筷子竖插在饭中（像供奉），不要用筷子传递食物。\n"
      "6. 泡温泉前必须先洗净身体，毛巾不要放入池中。纹身者可能被拒绝入浴。\n"
      "7. 排队文化：日本人非常重视排队秩序。\n"
      "8. 鞠躬是常见礼节，轻微点头即可表示感谢。"
    ),
    keywords=["日本", "礼仪", "文化", "禁忌", "习俗", "规矩", "注意事项"],
  ),

  # === Japan - Shopping ===
  KnowledgeEntry(
    title="日本购物退税指南",
    category="tips",
    destination="日本",
    content=(
      "日本购物退税政策：\n"
      "1. 消费税率：10%（食品为8%）。\n"
      "2. 退税门槛：同一店铺同一天消费满5,000日元（含税约5,500日元）。\n"
      "3. 退税方式：免税店直接免税 或 一般店铺事后退税。\n"
      "4. 所需证件：护照原件（需有短期滞在签证贴纸）。\n"
      "5. 免税商品分为消耗品（食品、化妆品）和一般商品（电器、衣服），不能混合计算。\n"
      "6. 消耗品须在30天内携带出境，不得在日本境内拆封使用。\n"
      "7. 推荐去大型药妆店（松本清、唐吉诃德）或电器城（秋叶原、BIC Camera）退税购物。\n"
      "8. 2024年起推行电子退税，流程更便捷。"
    ),
    keywords=["日本", "购物", "退税", "免税", "消费税", "药妆", "电器"],
  ),

  # === Japan - Onsen ===
  KnowledgeEntry(
    title="日本温泉文化与礼仪",
    category="culture",
    destination="日本",
    content=(
      "日本温泉（温泉/おんせん）指南：\n"
      "1. 温泉种类：露天风吕（室外）、内汤（室内）、�generic足汤（足浴，免费体验）。\n"
      "2. 入浴礼仪：必须先在洗场冲洗干净身体，再进入浴池。\n"
      "3. 毛巾不入池：小毛巾可放在头上或池边。\n"
      "4. 纹身问题：传统温泉拒绝纹身客人。但部分旅馆有私人风吕（包场温泉）可供选择。\n"
      "5. 推荐温泉地：箱根、别府、草津、有马、道后。\n"
      "6. 温泉旅馆（旅館）：体验含怀石料理的一泊二食套餐是日本特色。\n"
      "7. 男女分浴为主，少数有混浴。\n"
      "8. 泡完温泉不要用清水冲洗，保留矿物质对皮肤更好。"
    ),
    keywords=["日本", "温泉", "泡汤", "箱根", "别府", "草津", "旅馆", "风吕"],
  ),

  # === Japan - Food ===
  KnowledgeEntry(
    title="日本寿司鉴赏指南",
    category="food",
    destination="日本",
    content=(
      "日本寿司品鉴：\n"
      "1. 寿司类型：握寿司（にぎり）、卷寿司（まき）、散寿司（ちらし）、押寿司。\n"
      "2. 高级寿司店（omakase）：由师傅决定菜单，价格1-5万日元不等。需预约。\n"
      "3. 回转寿司：平价选择，100-500日元/盘。推荐连锁：スシロー、くら寿司。\n"
      "4. 吃法：可用手或筷子。蘸酱油时鱼肉朝下轻触即可，不要泡。\n"
      "5. 搭配：姜片（gari）用于清口，不要堆在寿司上。\n"
      "6. 推荐鱼种（按季节）：春-�的鯛鱼/初�的鰹鱼；夏-穴子；秋-鮭鱼/秋刀鱼；冬-金枪鱼/鰤鱼。\n"
      "7. 筑地/丰洲市场的场外市场是体验新鲜寿司的好去处。"
    ),
    keywords=["日本", "寿司", "美食", "餐厅", "omakase", "筑地", "丰洲", "回转寿司"],
  ),

  # === Thailand - Visa ===
  KnowledgeEntry(
    title="泰国签证政策（中国公民）",
    category="visa",
    destination="泰国",
    content=(
      "中国公民前往泰国签证选项：\n"
      "1. 免签入境（2024年起）：中国护照可免签入境泰国，停留不超过30天。\n"
      "2. 落地签：到达泰国机场后办理，停留15天，费用2000泰铢。需准备：护照、往返机票、酒店预订、2万泰铢现金证明。\n"
      "3. 旅游签证（提前办理）：有效期3个月，停留60天，可延期30天。\n"
      "入境注意：\n"
      "- 每人可携带不超过200支香烟，1升酒。\n"
      "- 禁止携带电子烟入境（违者可能被罚款或监禁）。\n"
      "- 携带超过2万美元等值外币须申报。"
    ),
    keywords=["泰国", "签证", "visa", "免签", "落地签", "入境", "电子烟"],
  ),

  # === Thailand - Culture ===
  KnowledgeEntry(
    title="泰国佛寺参拜礼仪",
    category="culture",
    destination="泰国",
    content=(
      "泰国寺庙参拜须知：\n"
      "1. 着装要求：必须穿过膝裤装/长裙，上衣须有袖、遮盖肩膀。部分寺庙门口可借用围巾。\n"
      "2. 脱鞋：进入大殿（ubosot）必须脱鞋。\n"
      "3. 不要触摸佛像或僧侣。女性尤其不可接触僧侣。\n"
      "4. 拍照：大部分寺庙允许室外拍照，但殿内可能禁止。注意标识。\n"
      "5. 脚底禁忌：不要用脚指向佛像或他人，坐下时脚底不要朝向佛像。\n"
      "6. 头部禁忌：不要触摸他人的头部（包括小孩）。\n"
      "7. 参拜时间：建议上午前往，避开正午高温。\n"
      "8. 推荐寺庙：大皇宫/玉佛寺、卧佛寺、郑王庙（以上曼谷），清迈双龙寺。"
    ),
    keywords=["泰国", "寺庙", "佛寺", "大皇宫", "礼仪", "文化", "参拜", "禁忌"],
  ),

  # === Thailand - Tips ===
  KnowledgeEntry(
    title="泰国小费文化与注意事项",
    category="tips",
    destination="泰国",
    content=(
      "泰国小费指南：\n"
      "1. 酒店行李员：20-50泰铢/次。\n"
      "2. 客房清洁：20-50泰铢/天，放在枕头上。\n"
      "3. 餐厅：高档餐厅通常含10%服务费，不含的话给50-100泰铢。路边摊不需要小费。\n"
      "4. 按摩/SPA：50-100泰铢，服务特别好可给更多。\n"
      "5. 出租车：不找零即可，或凑个整数。\n"
      "6. 注意：给小费不要给硬币（泰国认为硬币是给乞丐的），请用纸币。\n"
      "7. 最低面额：20泰铢纸币是最低小费单位。"
    ),
    keywords=["泰国", "小费", "礼仪", "消费", "注意事项", "tips"],
  ),

  # === Thailand - Food ===
  KnowledgeEntry(
    title="泰国街头小吃安全指南",
    category="food",
    destination="泰国",
    content=(
      "泰国街头小吃安全与推荐：\n"
      "1. 卫生原则：选人多的摊位（流转快、食材新鲜）。观察摊位是否干净、有无冰块保鲜。\n"
      "2. 饮水：不要喝自来水。购买瓶装水或便利店饮品。街头冰块通常是工厂制冰，相对安全。\n"
      "3. 推荐必吃：泰式炒河粉（Pad Thai）、绿咖喱（Green Curry）、芒果糯米饭、\n"
      "   冬阴功（Tom Yum）、青木瓜沙拉（Som Tam，注意辣度）、烤串（Moo Ping）。\n"
      "4. 过敏注意：泰餐大量使用花生、虾酱、鱼露，如有过敏请提前说明。\n"
      "5. 辣度：一定要说明辣度接受程度。\"ไม่เผ็ด\"（mai phet）= 不辣。\n"
      "6. 价格参考：街头小吃40-80泰铢/份，夜市80-150泰铢。\n"
      "7. 推荐夜市：曼谷拉差达火车夜市、清迈周日夜市、普吉班赞市场。"
    ),
    keywords=["泰国", "小吃", "街头美食", "夜市", "美食", "安全", "卫生", "Pad Thai"],
  ),

  # === Thailand - Entry ===
  KnowledgeEntry(
    title="泰国出入境须知",
    category="tips",
    destination="泰国",
    content=(
      "泰国出入境注意事项：\n"
      "1. 入境卡：部分口岸仍需填写入境卡（TM6），请在飞机上提前填好。\n"
      "2. 现金抽查：落地签旅客可能被抽查现金，个人需携带1万泰铢（约2000元），家庭2万泰铢。\n"
      "3. 禁止携带物品：电子烟、超量烟酒、毒品、色情制品。\n"
      "4. 出境注意：佛像（超过5寸）需文化部许可才能带出。\n"
      "5. 海关申报：超过5万泰铢现金出境需申报。\n"
      "6. SIM卡：机场有True/AIS/DTAC柜台，推荐购买7-15天旅游SIM卡（约300-500泰铢含流量和通话）。\n"
      "7. 换汇：市区Super Rich汇率最好，机场汇率偏低。建议先换少量应急，到市区再大量换。"
    ),
    keywords=["泰国", "出入境", "海关", "入境卡", "现金", "SIM卡", "换汇", "手机卡"],
  ),

  # === General - Packing ===
  KnowledgeEntry(
    title="旅行行李打包清单",
    category="tips",
    destination="general",
    content=(
      "旅行打包实用清单：\n"
      "【证件类】护照、签证复印件、身份证、机票行程单、酒店预订单、保险单。建议拍照备份到手机。\n"
      "【电子设备】手机+充电器、充电宝（飞机限2个/人,<160Wh）、万能转换插头、耳机。\n"
      "【日用品】牙刷牙膏、洗面奶、防晒霜（SPF50+）、墨镜、雨伞/雨衣。\n"
      "【药品】感冒药、止泻药、创可贴、晕车药、过敏药、肠胃药。\n"
      "【衣物】根据目的地天气准备；内衣袜子多带；一件薄外套（飞机/空调房）。\n"
      "【收纳技巧】衣物卷起来比叠省空间；用密封袋分类；贵重物品放随身包。\n"
      "【注意事项】液体类放行李托运；充电宝必须随身携带不可托运；打火机限随身1个。"
    ),
    keywords=["行李", "打包", "收纳", "清单", "准备", "必带", "携带", "托运"],
  ),

  # === General - Jet Lag ===
  KnowledgeEntry(
    title="时差调整与倒时差技巧",
    category="tips",
    destination="general",
    content=(
      "倒时差实用建议：\n"
      "1. 出发前3天开始逐步调整作息（向目的地时区靠拢1-2小时/天）。\n"
      "2. 飞机上：登机后立即调表为目的地时间，按当地时间作息。\n"
      "3. 到达后：白天多接触阳光有助调整生物钟。\n"
      "4. 饮食：避免到达首日暴饮暴食，清淡为主。\n"
      "5. 咖啡因：到达当天下午3点后避免咖啡/茶。\n"
      "6. 褪黑素：部分旅客服用小剂量褪黑素辅助入睡（建议咨询医生）。\n"
      "7. 常见时差参考：中国→日本+1h（几乎无感）、中国→泰国-1h、中国→欧洲-6~7h、中国→美西-15~16h。\n"
      "8. 规律：向东飞比向西飞更难适应。"
    ),
    keywords=["时差", "倒时差", "jet lag", "生物钟", "作息", "睡眠"],
  ),

  # === General - Insurance ===
  KnowledgeEntry(
    title="出境旅行保险建议",
    category="safety",
    destination="general",
    content=(
      "旅行保险选购指南：\n"
      "1. 必要性：出境游强烈建议购买旅行险，尤其是医疗费用高昂的地区（日本、美国、欧洲）。\n"
      "2. 核心保障：意外伤害、医疗费用（含紧急救援）、行李丢失/延误、航班延误/取消。\n"
      "3. 保额建议：亚洲目的地医疗保额≥30万元；欧美≥50万元。\n"
      "4. 注意事项：确认是否覆盖高风险运动（潜水、滑雪、蹦极）。\n"
      "5. 购买时机：出发前购买，部分保险要求提前24小时生效。\n"
      "6. 推荐平台：支付宝/微信保险、美亚保险、安联保险、平安旅行险。\n"
      "7. 理赔准备：保留所有医疗收据、报警记录、航空公司延误证明。\n"
      "8. 申根签证国家强制要求保险，医疗保额需≥3万欧元。"
    ),
    keywords=["保险", "旅行险", "医疗", "理赔", "意外", "安全", "申根"],
  ),

  # === General - Emergency ===
  KnowledgeEntry(
    title="海外紧急联系方式",
    category="safety",
    destination="general",
    content=(
      "海外紧急联系方式汇总：\n"
      "【中国领事保护】\n"
      "- 全球领事保护热线：+86-10-12308 或 +86-10-65612308\n"
      "- 外交部12308微信小程序可在线求助\n"
      "【各国报警电话】\n"
      "- 日本：110（报警）/ 119（火灾/急救）\n"
      "- 泰国：191（报警）/ 1155（旅游警察，会英文）\n"
      "- 韩国：112（报警）/ 119（急救）\n"
      "- 美国/加拿大：911\n"
      "- 欧洲通用：112\n"
      "- 澳洲：000\n"
      "【实用建议】\n"
      "- 出发前将护照信息页、签证页拍照保存到云端\n"
      "- 记录当地中国大使馆/领事馆地址和电话\n"
      "- 购买当地SIM卡确保通讯畅通\n"
      "- 下载目的地离线地图（Google Maps / 高德海外版）"
    ),
    keywords=[
      "紧急", "报警", "急救", "领事", "大使馆", "电话",
      "SOS", "安全", "求助",
    ],
  ),

  # === General - Currency ===
  KnowledgeEntry(
    title="出境游换汇与支付建议",
    category="tips",
    destination="general",
    content=(
      "海外换汇与支付实用建议：\n"
      "1. 换汇渠道：银行柜台（出发前）、机场兑换、当地兑换店、ATM取现。\n"
      "2. 汇率比较：银行>当地兑换店>机场。建议出发前在银行换一部分现金。\n"
      "3. 信用卡：Visa/Mastercard全球通用。日本和部分欧洲小店可能只收现金。\n"
      "4. 移动支付：支付宝/微信在东南亚和日韩部分商户可用，但不要完全依赖。\n"
      "5. ATM取现：银联卡可在境外有银联标识的ATM取现，手续费约12-15元/笔。\n"
      "6. 注意事项：通知银行你的出行计划，避免海外刷卡被风控冻结。\n"
      "7. 零钱准备：日本大量使用硬币，准备一个零钱包。泰国准备小额纸币用于小费。"
    ),
    keywords=["换汇", "货币", "支付", "信用卡", "ATM", "银联", "支付宝", "现金"],
  ),

  # === Japan - General Tips ===
  KnowledgeEntry(
    title="日本旅行综合贴士",
    category="tips",
    destination="日本",
    content=(
      "日本旅行实用贴士：\n"
      "1. Wi-Fi：推荐租用随身Wi-Fi（约25-35元/天）或购买流量SIM卡。\n"
      "2. 插座：日本使用110V/A型插头（两扁脚），与中国两脚插头通用，三脚需转换器。\n"
      "3. 便利店：7-11、全家、罗森是万能的。可买票、取钱、打印、寄快递。\n"
      "4. 药妆推荐：龙角散、SALONPAS、太田胃散、EVE止痛药、乐敦眼药水。\n"
      "5. 厕所：日本公共厕所非常干净且免费。智能马桶盖是一大特色。\n"
      "6. 营业时间：商店通常10:00-20:00，餐厅11:00-14:00/17:00-22:00。\n"
      "7. 礼貌用语：ありがとう（谢谢）、すみません（不好意思）很实用。\n"
      "8. 地震应对：日本多地震，了解酒店逃生路线，手机开启紧急地震速报。"
    ),
    keywords=["日本", "贴士", "Wi-Fi", "插座", "便利店", "药妆", "实用", "出行"],
  ),

  # === Thailand - General Tips ===
  KnowledgeEntry(
    title="泰国旅行综合贴士",
    category="tips",
    destination="泰国",
    content=(
      "泰国旅行实用贴士：\n"
      "1. 气候：全年炎热，11-2月凉季最适合旅行。4月最热（泼水节/宋干节）。\n"
      "2. 交通：曼谷推荐BTS轻轨+MRT地铁；短途用Grab打车（类似滴滴）。\n"
      "3. 插座：泰国220V，两扁脚插头与中国通用。\n"
      "4. 王室尊重：泰国法律规定不得侮辱王室成员，不要踩踏带有国王头像的纸币。\n"
      "5. 砍价：夜市和水上市场可以砍价，商场和便利店不砍价。\n"
      "6. 防晒：紫外线强烈，SPF50+防晒霜必备。\n"
      "7. 出租车：上车前确认打表（by meter），否则容易被宰。\n"
      "8. 大象体验：选择道德大象保护营地，避免骑大象。"
    ),
    keywords=["泰国", "贴士", "气候", "交通", "Grab", "防晒", "出行", "实用"],
  ),

  # === Japan - Accommodation ===
  KnowledgeEntry(
    title="日本住宿类型全解",
    category="tips",
    destination="日本",
    content=(
      "日本住宿类型介绍：\n"
      "1. 商务酒店：东横INN、APA、Route Inn等连锁，干净便宜（5000-10000日元/晚），房间小。\n"
      "2. 温泉旅馆（旅館）：传统日式体验，含温泉+怀石料理，15000-50000日元/晚。\n"
      "3. 胶囊旅馆：独特体验，2000-5000日元/晚，适合独行背包客。\n"
      "4. 民宿（Airbnb）：日本民宿法规严格，确认房东有合法许可。\n"
      "5. 青年旅舍：2000-4000日元/晚，适合交友和预算有限者。\n"
      "6. 高级酒店：帝国饭店、安缦、虹夕诺雅等，体验顶级日式服务。\n"
      "7. 预订建议：热门季节（樱花季3-4月、红叶季11月、新年）提前2-3个月预订。"
    ),
    keywords=["日本", "住宿", "酒店", "旅馆", "民宿", "胶囊", "预订", "温泉旅馆"],
  ),

  # === General - Photography Tips ===
  KnowledgeEntry(
    title="旅行摄影与拍照建议",
    category="tips",
    destination="general",
    content=(
      "旅行摄影实用建议：\n"
      "1. 黄金时间：日出后1小时和日落前1小时光线最美。\n"
      "2. 构图三分法：将主体放在画面三分之一线交叉点。\n"
      "3. 人少技巧：热门景点建议早上8点前到达，避开旅行团。\n"
      "4. 器材建议：手机足够旅行记录；追求画质可带微单+一支变焦镜头。\n"
      "5. 备份：每天将照片备份到云端或移动硬盘，防止丢失。\n"
      "6. 注意事项：部分场所禁止拍照（博物馆、寺庙内部），请尊重当地规定。\n"
      "7. 请求许可：拍摄当地人前请先征得同意。\n"
      "8. 充电：多带一块备用电池，重要时刻不要没电。"
    ),
    keywords=["摄影", "拍照", "拍摄", "照片", "相机", "构图", "打卡"],
  ),

  # === Korea - Visa ===
  KnowledgeEntry(
    title="韩国签证政策（中国公民）",
    category="visa",
    destination="韩国",
    content=(
      "中国公民前往韩国签证说明：\n"
      "1. 单次旅游签证（C-3-9）：停留90天以内，需提供在职证明、收入证明、行程等。\n"
      "2. 五年多次签证：符合条件者（高收入/曾多次访韩）可申请。\n"
      "3. 济州岛免签：中国公民可免签入境济州岛，停留30天。仅限济州岛范围。\n"
      "4. 过境免签：转机前往第三国可在仁川机场区域停留72小时（需持有联程机票）。\n"
      "5. 办理方式：通过韩国驻华大使馆/领事馆或签证代办机构。\n"
      "6. 审核周期：通常5-7个工作日。旺季可能延长。"
    ),
    keywords=["韩国", "签证", "visa", "济州岛", "免签", "过境"],
  ),

  # === General - WiFi & Communication ===
  KnowledgeEntry(
    title="出境通讯与网络方案",
    category="tips",
    destination="general",
    content=(
      "出境旅行通讯方案对比：\n"
      "1. 国际漫游：最方便但最贵。中国移动/联通/电信均有日套餐（25-60元/天）。\n"
      "2. 当地SIM卡：最划算。到达机场后购买，通常含流量+本地通话。\n"
      "3. 随身Wi-Fi：适合多人共享。租赁价格15-40元/天，需充电携带。\n"
      "4. eSIM：支持eSIM的手机可在线购买虚拟SIM卡，无需实体卡，即买即用。\n"
      "5. 推荐方案：\n"
      "   - 日本：IIJmio eSIM 或机场购买Bmobile SIM\n"
      "   - 泰国：True/AIS旅游SIM（机场柜台）\n"
      "   - 韩国：KT/SK Telecom旅游SIM\n"
      "6. VPN注意：部分国家有网络限制，提前准备好VPN工具。"
    ),
    keywords=["通讯", "网络", "Wi-Fi", "SIM卡", "eSIM", "漫游", "上网", "流量"],
  ),
]


class KnowledgeBase:
  """In-memory knowledge base with keyword-matching retrieval.

  Designed for easy migration to pgvector / embedding-based search.
  Currently uses TF-style keyword overlap scoring.
  """

  def __init__(self) -> None:
    self._entries: List[KnowledgeEntry] = list(_BUILTIN_ENTRIES)

  @property
  def size(self) -> int:
    return len(self._entries)

  def add_entry(self, entry: KnowledgeEntry) -> None:
    """Add a custom knowledge entry."""
    self._entries.append(entry)

  # ---------------------------------------------------------------- #
  # Core search
  # ---------------------------------------------------------------- #

  def search(
    self,
    query: str,
    destination: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5,
  ) -> List[Dict]:
    """Keyword-matching search with destination and category boosting.

    Returns a list of dicts with keys: title, category, destination,
    content, score.
    """
    try:
      query_tokens = self._tokenize(query)
      if not query_tokens:
        return []

      scored: List[tuple] = []
      for entry in self._entries:
        score = self._score_entry(entry, query_tokens, destination, category)
        if score > 0:
          scored.append((score, entry))

      # Sort descending by score
      scored.sort(key=lambda x: x[0], reverse=True)

      results: List[Dict] = []
      for score, entry in scored[:top_k]:
        results.append({
          "title": entry.title,
          "category": entry.category,
          "destination": entry.destination,
          "content": entry.content,
          "score": round(score, 3),
        })

      return results

    except Exception as exc:
      logger.warning("KnowledgeBase.search failed: %s", exc)
      return []

  # ---------------------------------------------------------------- #
  # Convenience methods
  # ---------------------------------------------------------------- #

  def get_destination_tips(self, destination: str) -> List[Dict]:
    """Get all tips for a specific destination."""
    return self.search(
      query=destination,
      destination=destination,
      category="tips",
      top_k=10,
    )

  def get_visa_info(
    self,
    destination: str,
    nationality: str = "CN",
  ) -> List[Dict]:
    """Get visa information for a destination.

    Currently nationality is unused (all entries are CN-centric)
    but the parameter is reserved for future multi-nationality support.
    """
    results = self.search(
      query=f"{destination} 签证",
      destination=destination,
      category="visa",
      top_k=3,
    )
    if not results:
      # Fallback: broader search without category filter
      results = self.search(
        query=f"{destination} 签证 入境",
        destination=destination,
        top_k=3,
      )
    return results

  def get_culture_info(self, destination: str) -> List[Dict]:
    """Get cultural tips and taboos for a destination."""
    return self.search(
      query=f"{destination} 文化 礼仪",
      destination=destination,
      category="culture",
      top_k=5,
    )

  def get_food_info(self, destination: str) -> List[Dict]:
    """Get food recommendations for a destination."""
    return self.search(
      query=f"{destination} 美食",
      destination=destination,
      category="food",
      top_k=5,
    )

  # ---------------------------------------------------------------- #
  # Internal scoring
  # ---------------------------------------------------------------- #

  def _tokenize(self, text: str) -> List[str]:
    """Simple tokenization: split on non-word chars + Chinese chars."""
    # Extract Chinese characters individually and English words
    tokens: List[str] = []
    # Chinese chars
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in chinese:
      # Each Chinese character and bigrams
      for ch in seg:
        tokens.append(ch)
      for i in range(len(seg) - 1):
        tokens.append(seg[i:i + 2])
    # English words
    english = re.findall(r"[a-zA-Z]{2,}", text.lower())
    tokens.extend(english)
    return tokens

  def _score_entry(
    self,
    entry: KnowledgeEntry,
    query_tokens: List[str],
    destination: Optional[str],
    category: Optional[str],
  ) -> float:
    """Compute relevance score for an entry against query tokens."""
    score = 0.0

    # Build entry text for matching
    entry_text = (
      f"{entry.title} {entry.destination} "
      f"{' '.join(entry.keywords)} {entry.content}"
    ).lower()
    entry_tokens_set = set(self._tokenize(entry_text))

    # Keyword overlap score
    if query_tokens:
      overlap = sum(1 for t in query_tokens if t in entry_tokens_set)
      score += overlap / len(query_tokens) * 10.0

    # Exact keyword matches (boost)
    for kw in entry.keywords:
      kw_lower = kw.lower()
      for qt in query_tokens:
        if qt in kw_lower or kw_lower in qt:
          score += 2.0

    # Destination match bonus
    if destination:
      dest_lower = destination.lower()
      entry_dest_lower = entry.destination.lower()
      if dest_lower in entry_dest_lower or entry_dest_lower in dest_lower:
        score += 5.0
      elif entry.destination == "general":
        score += 1.0

    # Category match bonus
    if category:
      if entry.category == category:
        score += 3.0

    return score

  def format_results(self, results: List[Dict], max_entries: int = 3) -> str:
    """Format search results into a readable string for prompt injection."""
    if not results:
      return "No relevant knowledge found."

    parts: List[str] = []
    for item in results[:max_entries]:
      parts.append(
        f"### {item['title']}\n"
        f"[{item['category']}] {item['destination']}\n\n"
        f"{item['content']}"
      )
    return "\n\n---\n\n".join(parts)


# Singleton instance
knowledge_base = KnowledgeBase()
