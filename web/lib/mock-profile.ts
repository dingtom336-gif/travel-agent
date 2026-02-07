// Mock data for profile page

export interface UserProfile {
  id: string;
  name: string;
  avatarUrl: string | null;
  email: string;
  memberLevel: string;
  totalTrips: number;
  totalDestinations: number;
  joinDate: string;
}

export interface TripItem {
  id: string;
  destination: string;
  startDate: string;
  endDate: string;
  status: "draft" | "confirmed" | "in_progress" | "completed";
  coverImage: string | null;
  travelers: number;
  totalBudget: number;
  currency: string;
}

export interface FavoriteItem {
  id: string;
  name: string;
  type: "attraction" | "hotel" | "guide";
  rating: number;
  imageUrl: string | null;
  location: string;
}

export type TravelStyle = "adventure" | "leisure" | "cultural" | "business";
export type BudgetLevel = "economy" | "comfort" | "luxury";
export type AccommodationType = "hotel" | "homestay" | "hostel";
export type TransportPref = "direct" | "economy" | "time";
export type DietaryRestriction = "vegetarian" | "halal" | "none";

export interface UserPreferences {
  travelStyles: TravelStyle[];
  budgetLevel: BudgetLevel;
  accommodations: AccommodationType[];
  transportPref: TransportPref;
  dietaryRestrictions: DietaryRestriction[];
}

// Label maps for display
export const travelStyleLabels: Record<TravelStyle, { label: string; icon: string }> = {
  adventure: { label: "冒险探索", icon: "mountain" },
  leisure: { label: "休闲度假", icon: "sun" },
  cultural: { label: "人文艺术", icon: "palette" },
  business: { label: "商务出行", icon: "briefcase" },
};

export const budgetLevelLabels: Record<BudgetLevel, { label: string; desc: string }> = {
  economy: { label: "经济实惠", desc: "追求性价比，精打细算" },
  comfort: { label: "舒适品质", desc: "适度消费，品质体验" },
  luxury: { label: "奢华享受", desc: "不限预算，极致体验" },
};

export const accommodationLabels: Record<AccommodationType, { label: string; icon: string }> = {
  hotel: { label: "酒店", icon: "building" },
  homestay: { label: "民宿", icon: "home" },
  hostel: { label: "青旅", icon: "bed" },
};

export const transportPrefLabels: Record<TransportPref, { label: string; desc: string }> = {
  direct: { label: "直飞优先", desc: "减少中转，节省时间" },
  economy: { label: "经济优先", desc: "价格最低，可接受中转" },
  time: { label: "时间优先", desc: "最快到达，不限价格" },
};

export const dietaryLabels: Record<DietaryRestriction, { label: string; icon: string }> = {
  vegetarian: { label: "素食", icon: "leaf" },
  halal: { label: "清真", icon: "moon" },
  none: { label: "无限制", icon: "utensils" },
};

// --- Mock data instances ---

export const mockUser: UserProfile = {
  id: "user-001",
  name: "旅行者小明",
  avatarUrl: null,
  email: "xiaoming@example.com",
  memberLevel: "黄金会员",
  totalTrips: 12,
  totalDestinations: 8,
  joinDate: "2024-06-15",
};

export const mockTrips: TripItem[] = [
  {
    id: "itin-001",
    destination: "东京 + 大阪",
    startDate: "2026-01-25",
    endDate: "2026-01-29",
    status: "completed",
    coverImage: null,
    travelers: 3,
    totalBudget: 20000,
    currency: "CNY",
  },
  {
    id: "itin-002",
    destination: "巴厘岛",
    startDate: "2026-03-10",
    endDate: "2026-03-15",
    status: "confirmed",
    coverImage: null,
    travelers: 2,
    totalBudget: 15000,
    currency: "CNY",
  },
  {
    id: "itin-003",
    destination: "成都 + 九寨沟",
    startDate: "2025-10-01",
    endDate: "2025-10-05",
    status: "completed",
    coverImage: null,
    travelers: 4,
    totalBudget: 8000,
    currency: "CNY",
  },
  {
    id: "itin-004",
    destination: "北海道",
    startDate: "2026-12-20",
    endDate: "2026-12-25",
    status: "draft",
    coverImage: null,
    travelers: 2,
    totalBudget: 25000,
    currency: "CNY",
  },
];

export const mockFavorites: FavoriteItem[] = [
  {
    id: "fav-001",
    name: "浅草寺",
    type: "attraction",
    rating: 4.7,
    imageUrl: null,
    location: "东京，日本",
  },
  {
    id: "fav-002",
    name: "安缦东京",
    type: "hotel",
    rating: 4.9,
    imageUrl: null,
    location: "东京，日本",
  },
  {
    id: "fav-003",
    name: "巴厘岛完全攻略",
    type: "guide",
    rating: 4.8,
    imageUrl: null,
    location: "巴厘岛，印尼",
  },
  {
    id: "fav-004",
    name: "金阁寺",
    type: "attraction",
    rating: 4.6,
    imageUrl: null,
    location: "京都，日本",
  },
  {
    id: "fav-005",
    name: "九寨沟自由行指南",
    type: "guide",
    rating: 4.5,
    imageUrl: null,
    location: "四川，中国",
  },
  {
    id: "fav-006",
    name: "悦榕庄巴厘岛",
    type: "hotel",
    rating: 4.8,
    imageUrl: null,
    location: "巴厘岛，印尼",
  },
];

export const mockPreferences: UserPreferences = {
  travelStyles: ["leisure", "cultural"],
  budgetLevel: "comfort",
  accommodations: ["hotel", "homestay"],
  transportPref: "direct",
  dietaryRestrictions: ["none"],
};
