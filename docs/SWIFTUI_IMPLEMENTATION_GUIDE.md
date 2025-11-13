# SwiftUI Implementation Guide
## Typed ID Integration for iOS App

This guide shows you how to update your SwiftUI app to work with the new typed IDs.

## 🔄 Key Changes

### Field Naming Convention
All profile IDs now use typed naming:
- ✅ `buyer_id` instead of `public_id` (Buyer profiles)
- ✅ `builder_id` instead of `public_id` (Builder profiles)
- ✅ `community_id` instead of `public_id` (Communities)
- ✅ `sales_rep_id` instead of `public_id` (Sales reps)
- ✅ `community_admin_id` instead of `public_id` (Community admins)
- ✅ `user_id` instead of `public_id` (Users)

### Foreign Key References
All `user_id` foreign keys now reference **STRING** user IDs (e.g., "USR-xxx"), not integers:
- `buyer_profiles.user_id` → `users.user_id` (string FK)
- `builder_profiles.user_id` → `users.user_id` (string FK)
- `communities.user_id` → `users.user_id` (string FK, optional)
- `sales_reps.user_id` → `users.user_id` (string FK, optional)
- `community_admin_profiles.user_id` → `users.user_id` (string FK)

### Field Mapping Summary

| Swift Property | Backend Field | Type | Example Value |
|---|---|---|---|
| `BuyerProfile.id` | `buyer_id` | String | "BYR-1699564234-A7K9M2" |
| `BuyerProfile.userId` | `user_id` | String | "USR-1699564234-A7K9M2" |
| `BuilderProfile.id` | `builder_id` | String | "BLD-1699564234-X3P8Q1" |
| `BuilderProfile.userId` | `user_id` | String | "USR-1699564234-A7K9M2" |
| `Community.id` | `community_id` | String | "CMY-1699564234-Z5R7N4" |
| `Community.userId` | `user_id` | String? | "USR-1699564234-A7K9M2" |

---

## 📱 Part 1: Update SwiftUI Models

### 1. Buyer Profile Model

**File:** `Models/BuyerProfile.swift`

```swift
import Foundation

// MARK: - Buyer Profile Model
struct BuyerProfile: Codable, Identifiable {
    // Buyer ID - unique identifier for this buyer profile (BYR-xxx)
    let id: String  // Maps to backend's buyer_id, e.g., "BYR-1699564234-A7K9M2"
    // User ID - FK reference to the user who owns this profile (USR-xxx)
    let userId: String  // Maps to backend's user_id, e.g., "USR-1699564234-A7K9M2"

    // Social engagement
    let followersCount: Int

    // Identity / Display
    var displayName: String?
    var firstName: String
    var lastName: String
    var profileImage: String?
    var bio: String?
    var location: String?
    var websiteUrl: String?

    // Contact
    var email: String
    var phone: String?
    var phoneE164: String?
    var contactEmail: String?
    var contactPhone: String?
    var contactPreferred: ContactChannel

    // Address
    var address: String?
    var city: String?
    var state: String?
    var zipCode: String?

    // Core attributes
    var sex: Sex?
    var timeline: BuyTimeline

    // Financing
    var financingStatus: FinancingStatus
    var loanProgram: LoanProgram?
    var householdIncomeUsd: Int?
    var budgetMinUsd: Int?
    var budgetMaxUsd: Int?
    var downPaymentPercent: Int?
    var lenderName: String?
    var agentName: String?

    // Metadata
    var extra: [String: AnyCodable]?

    // Timestamps
    let createdAt: Date
    let updatedAt: Date

    // MARK: - Coding Keys
    enum CodingKeys: String, CodingKey {
        case id = "buyer_id"  // Backend field is buyer_id
        case userId = "user_id"  // Backend FK is user_id (string)
        case followersCount = "followers_count"
        case displayName = "display_name"
        case firstName = "first_name"
        case lastName = "last_name"
        case profileImage = "profile_image"
        case bio
        case location
        case websiteUrl = "website_url"
        case email
        case phone
        case phoneE164 = "phone_e164"
        case contactEmail = "contact_email"
        case contactPhone = "contact_phone"
        case contactPreferred = "contact_preferred"
        case address
        case city
        case state
        case zipCode = "zip_code"
        case sex
        case timeline
        case financingStatus = "financing_status"
        case loanProgram = "loan_program"
        case householdIncomeUsd = "household_income_usd"
        case budgetMinUsd = "budget_min_usd"
        case budgetMaxUsd = "budget_max_usd"
        case downPaymentPercent = "down_payment_percent"
        case lenderName = "lender_name"
        case agentName = "agent_name"
        case extra
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    // MARK: - Helper computed properties
    var fullName: String {
        "\(firstName) \(lastName)".trimmingCharacters(in: .whitespaces)
    }

    var budgetRange: String? {
        guard let min = budgetMinUsd, let max = budgetMaxUsd else { return nil }
        return "$\(min.formatted()) - $\(max.formatted())"
    }
}

// MARK: - Enums
enum Sex: String, Codable {
    case female
    case male
    case nonBinary = "non_binary"
    case other
    case preferNot = "prefer_not"
}

enum BuyTimeline: String, Codable {
    case immediately
    case oneToThreeMonths = "one_to_three_months"
    case threeToSixMonths = "three_to_six_months"
    case sixPlusMonths = "six_plus_months"
    case exploring

    var displayText: String {
        switch self {
        case .immediately: return "Immediately"
        case .oneToThreeMonths: return "1-3 Months"
        case .threeToSixMonths: return "3-6 Months"
        case .sixPlusMonths: return "6+ Months"
        case .exploring: return "Just Exploring"
        }
    }
}

enum FinancingStatus: String, Codable {
    case cash
    case preApproved = "pre_approved"
    case preQualified = "pre_qualified"
    case needsPreApproval = "needs_pre_approval"
    case unknown

    var displayText: String {
        switch self {
        case .cash: return "Cash Buyer"
        case .preApproved: return "Pre-Approved"
        case .preQualified: return "Pre-Qualified"
        case .needsPreApproval: return "Needs Pre-Approval"
        case .unknown: return "Unknown"
        }
    }
}

enum LoanProgram: String, Codable {
    case conventional
    case fha
    case va
    case usda
    case jumbo
    case other
}

enum ContactChannel: String, Codable {
    case email
    case phone
    case sms
    case inApp = "in_app"
}

// MARK: - AnyCodable for extra field
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else {
            value = try container.decode([String: AnyCodable].self)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let bool = value as? Bool {
            try container.encode(bool)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let string = value as? String {
            try container.encode(string)
        } else if let dict = value as? [String: AnyCodable] {
            try container.encode(dict)
        }
    }
}

// MARK: - Sample Data (for previews)
extension BuyerProfile {
    static var sample: BuyerProfile {
        BuyerProfile(
            id: "BYR-1699564234-A7K9M2",
            userId: "USR-1699564234-A7K9M2",
            followersCount: 42,
            displayName: "John Doe",
            firstName: "John",
            lastName: "Doe",
            profileImage: nil,
            bio: "Looking for my dream home in Houston!",
            location: "Houston, TX",
            websiteUrl: nil,
            email: "john@example.com",
            phone: "713-555-0100",
            phoneE164: "+17135550100",
            contactEmail: "john@example.com",
            contactPhone: "713-555-0100",
            contactPreferred: .email,
            address: "123 Main St",
            city: "Houston",
            state: "TX",
            zipCode: "77001",
            sex: .male,
            timeline: .threeToSixMonths,
            financingStatus: .preApproved,
            loanProgram: .conventional,
            householdIncomeUsd: 150000,
            budgetMinUsd: 300000,
            budgetMaxUsd: 500000,
            downPaymentPercent: 20,
            lenderName: "ABC Mortgage",
            agentName: nil,
            extra: nil,
            createdAt: Date(),
            updatedAt: Date()
        )
    }
}
```

---

### 2. Builder Profile Model

**File:** `Models/BuilderProfile.swift`

```swift
import Foundation

struct BuilderProfile: Codable, Identifiable {
    // Builder ID - unique identifier for this builder profile (BLD-xxx)
    let id: String  // Maps to backend's builder_id, e.g., "BLD-1699564234-X3P8Q1"
    // User ID - FK reference to the user who owns this profile (USR-xxx)
    let userId: String  // Maps to backend's user_id, e.g., "USR-1699564234-A7K9M2"

    // Core fields
    var name: String
    var website: String?
    var specialties: [String]?
    var rating: Double?
    var communitiesServed: [String]?

    // Extended fields
    var about: String?
    var phone: String?
    var email: String?
    var address: String?
    var city: String?
    var state: String?
    var postalCode: String?
    var verified: Bool

    // Metadata
    var title: String?
    var bio: String?
    var socials: [String: String]?

    // Timestamps
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id = "builder_id"  // Backend field is builder_id
        case userId = "user_id"  // Backend FK is user_id (string)
        case name
        case website
        case specialties
        case rating
        case communitiesServed = "communities_served"
        case about
        case phone
        case email
        case address
        case city
        case state
        case postalCode = "postal_code"
        case verified
        case title
        case bio
        case socials
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    static var sample: BuilderProfile {
        BuilderProfile(
            id: "BLD-1699564234-X3P8Q1",
            userId: "USR-1699564567-B8L0N5",
            name: "ABC Homes",
            website: "https://abchomes.com",
            specialties: ["Custom Homes", "Energy Efficient"],
            rating: 4.8,
            communitiesServed: ["Houston", "The Woodlands"],
            about: "Building quality homes since 1990",
            phone: "713-555-0200",
            email: "info@abchomes.com",
            address: "456 Builder St",
            city: "Houston",
            state: "TX",
            postalCode: "77002",
            verified: true,
            title: "Premier Home Builder",
            bio: "Award-winning builder",
            socials: ["linkedin": "abc-homes"],
            createdAt: Date(),
            updatedAt: Date()
        )
    }
}
```

---

### 3. Community Model

**File:** `Models/Community.swift`

```swift
import Foundation

struct Community: Codable, Identifiable {
    // Community ID - unique identifier for this community (CMY-xxx)
    let id: String  // Maps to backend's community_id, e.g., "CMY-1699564234-Z5R7N4"

    // Owner/Creator reference (FK to user who owns/created this community)
    var userId: String?  // Maps to backend's user_id, e.g., "USR-1699564234-A7K9M2"

    var name: String
    var city: String?
    var state: String?
    var postalCode: String?

    // Finance
    var communityDues: String?
    var taxRate: String?
    var monthlyFee: String?

    // Meta
    var followers: Int
    var about: String?
    var isVerified: Bool

    // Stats
    var homes: Int
    var residents: Int
    var foundedYear: Int?
    var memberCount: Int

    // Development
    var developmentStage: String?
    var enterpriseNumberHoa: String?

    // Media
    var introVideoUrl: String?
    var communityWebsiteUrl: String?

    // Timestamps
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id = "community_id"  // Backend field is community_id
        case userId = "user_id"  // Backend FK is user_id (string, optional)
        case name
        case city
        case state
        case postalCode = "postal_code"
        case communityDues = "community_dues"
        case taxRate = "tax_rate"
        case monthlyFee = "monthly_fee"
        case followers
        case about
        case isVerified = "is_verified"
        case homes
        case residents
        case foundedYear = "founded_year"
        case memberCount = "member_count"
        case developmentStage = "development_stage"
        case enterpriseNumberHoa = "enterprise_number_hoa"
        case introVideoUrl = "intro_video_url"
        case communityWebsiteUrl = "community_website_url"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}
```

---

## 📡 Part 2: API Client Implementation

### API Client with Public ID Support

**File:** `Services/APIClient.swift`

```swift
import Foundation

class APIClient {
    static let shared = APIClient()

    private let baseURL = "https://api.yourdomain.com/api/v1"
    private let session: URLSession

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        self.session = URLSession(configuration: config)
    }

    // MARK: - Auth Token Management
    private var authToken: String? {
        // Get from Keychain or UserDefaults
        UserDefaults.standard.string(forKey: "auth_token")
    }

    // MARK: - Generic Request Method
    private func request<T: Decodable>(
        method: String,
        endpoint: String,
        body: Encodable? = nil
    ) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token if available
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Encode body if provided
        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        // Make request
        let (data, response) = try await session.data(for: request)

        // Check response
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        // Decode response
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        return try decoder.decode(T.self, from: data)
    }

    // MARK: - Buyer Endpoints

    /// Get buyer profile by buyer ID (NEW ENDPOINT - Recommended)
    func getBuyer(buyerId: String) async throws -> BuyerProfile {
        return try await request(
            method: "GET",
            endpoint: "/buyers/\(buyerId)"
        )
    }

    /// Update buyer profile by buyer ID
    func updateBuyer(buyerId: String, updates: BuyerProfileUpdate) async throws -> BuyerProfile {
        return try await request(
            method: "PATCH",
            endpoint: "/buyers/\(buyerId)",
            body: updates
        )
    }

    /// Delete buyer profile
    func deleteBuyer(buyerId: String) async throws {
        let _: EmptyResponse = try await request(
            method: "DELETE",
            endpoint: "/buyers/\(buyerId)"
        )
    }

    /// Create buyer profile for user (LEGACY - User-based)
    func createBuyerForUser(userId: String, profile: BuyerProfileCreate) async throws -> BuyerProfile {
        return try await request(
            method: "POST",
            endpoint: "/users/\(userId)/buyer",
            body: profile
        )
    }

    // MARK: - Builder Endpoints

    /// Get builder profile by builder ID
    func getBuilder(builderId: String) async throws -> BuilderProfile {
        return try await request(
            method: "GET",
            endpoint: "/builders/\(builderId)"
        )
    }

    /// Update builder profile
    func updateBuilder(builderId: String, updates: BuilderProfileUpdate) async throws -> BuilderProfile {
        return try await request(
            method: "PATCH",
            endpoint: "/builders/\(builderId)",
            body: updates
        )
    }

    // MARK: - Community Endpoints

    /// Get community by community ID
    func getCommunity(communityId: String) async throws -> Community {
        return try await request(
            method: "GET",
            endpoint: "/communities/\(communityId)"
        )
    }

    /// List all communities
    func listCommunities() async throws -> [Community] {
        return try await request(
            method: "GET",
            endpoint: "/communities"
        )
    }

    // MARK: - Tours Endpoints

    /// Get tours for buyer
    func getBuyerTours(buyerId: String) async throws -> [BuyerTour] {
        return try await request(
            method: "GET",
            endpoint: "/buyers/\(buyerId)/tours"
        )
    }

    /// Create tour for buyer
    func createTour(buyerId: String, tour: BuyerTourCreate) async throws -> BuyerTour {
        return try await request(
            method: "POST",
            endpoint: "/buyers/\(buyerId)/tours",
            body: tour
        )
    }
}

// MARK: - Request/Response Models

struct BuyerProfileCreate: Codable {
    var displayName: String?
    var firstName: String?
    var lastName: String?
    var email: String?
    var phone: String?
    var timeline: BuyTimeline?
    var financingStatus: FinancingStatus?
    var budgetMinUsd: Int?
    var budgetMaxUsd: Int?

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case firstName = "first_name"
        case lastName = "last_name"
        case email
        case phone
        case timeline
        case financingStatus = "financing_status"
        case budgetMinUsd = "budget_min_usd"
        case budgetMaxUsd = "budget_max_usd"
    }
}

struct BuyerProfileUpdate: Codable {
    var displayName: String?
    var bio: String?
    var budgetMinUsd: Int?
    var budgetMaxUsd: Int?
    var timeline: BuyTimeline?

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case bio
        case budgetMinUsd = "budget_min_usd"
        case budgetMaxUsd = "budget_max_usd"
        case timeline
    }
}

struct BuilderProfileUpdate: Codable {
    var name: String?
    var about: String?
    var phone: String?
    var email: String?
}

struct BuyerTour: Codable, Identifiable {
    let id: Int
    let buyerId: Int
    let propertyId: Int?
    var scheduledAt: Date?
    var status: String
    var note: String?

    enum CodingKeys: String, CodingKey {
        case id
        case buyerId = "buyer_id"
        case propertyId = "property_id"
        case scheduledAt = "scheduled_at"
        case status
        case note
    }
}

struct BuyerTourCreate: Codable {
    var propertyId: Int?
    var scheduledAt: Date?
    var note: String?

    enum CodingKeys: String, CodingKey {
        case propertyId = "property_id"
        case scheduledAt = "scheduled_at"
        case note
    }
}

struct EmptyResponse: Codable {}

// MARK: - API Errors

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
    case decodingError(Error)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError(let error):
            return "Decoding error: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}
```

---

## 🎨 Part 3: SwiftUI View Examples

### Example: Buyer Profile View

**File:** `Views/BuyerProfileView.swift`

```swift
import SwiftUI

struct BuyerProfileView: View {
    let buyerId: String  // NOW: BYR-xxx instead of UUID

    @State private var buyer: BuyerProfile?
    @State private var isLoading = false
    @State private var error: Error?

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading profile...")
            } else if let buyer = buyer {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        // Header
                        HStack {
                            if let imageURL = buyer.profileImage {
                                AsyncImage(url: URL(string: imageURL)) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    Circle()
                                        .fill(Color.gray.opacity(0.3))
                                }
                                .frame(width: 80, height: 80)
                                .clipShape(Circle())
                            }

                            VStack(alignment: .leading) {
                                Text(buyer.displayName ?? buyer.fullName)
                                    .font(.title2)
                                    .bold()

                                Text(buyer.location ?? "No location")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)

                                HStack {
                                    Image(systemName: "person.2.fill")
                                    Text("\(buyer.followersCount) followers")
                                }
                                .font(.caption)
                                .foregroundColor(.secondary)
                            }
                        }
                        .padding()

                        Divider()

                        // Bio
                        if let bio = buyer.bio {
                            VStack(alignment: .leading) {
                                Text("About")
                                    .font(.headline)
                                Text(bio)
                                    .font(.body)
                            }
                            .padding()
                        }

                        Divider()

                        // Timeline
                        VStack(alignment: .leading) {
                            Text("Buying Timeline")
                                .font(.headline)
                            Text(buyer.timeline.displayText)
                                .font(.body)
                        }
                        .padding()

                        // Budget
                        if let budgetRange = buyer.budgetRange {
                            VStack(alignment: .leading) {
                                Text("Budget")
                                    .font(.headline)
                                Text(budgetRange)
                                    .font(.body)
                            }
                            .padding()
                        }

                        // Financing Status
                        VStack(alignment: .leading) {
                            Text("Financing")
                                .font(.headline)
                            Text(buyer.financingStatus.displayText)
                                .font(.body)
                        }
                        .padding()
                    }
                }
            } else if let error = error {
                Text("Error: \(error.localizedDescription)")
                    .foregroundColor(.red)
            }
        }
        .navigationTitle("Buyer Profile")
        .task {
            await loadBuyer()
        }
    }

    @MainActor
    private func loadBuyer() async {
        isLoading = true
        defer { isLoading = false }

        do {
            buyer = try await APIClient.shared.getBuyer(buyerId: buyerId)
        } catch {
            self.error = error
        }
    }
}

#Preview {
    NavigationView {
        BuyerProfileView(buyerId: "BYR-1699564234-A7K9M2")
    }
}
```

---

### Example: Using in Navigation

```swift
// OLD: Using UUID
NavigationLink(destination: BuyerProfileView(buyerId: UUID())) {
    Text("View Profile")
}

// NEW: Using String ID
NavigationLink(destination: BuyerProfileView(buyerId: "BYR-1699564234-A7K9M2")) {
    Text("View Profile")
}

// From API response
ForEach(buyers) { buyer in
    NavigationLink(destination: BuyerProfileView(buyerId: buyer.id)) {
        BuyerRow(buyer: buyer)
    }
}
```

---

## 📝 Part 4: Migration Checklist for iOS App

### Step 1: Update Models
- [ ] Change `id` from `UUID` to `String` in all models
- [ ] Update `Identifiable` conformance (String works automatically)
- [ ] Update sample data for previews

### Step 2: Update API Client
- [ ] Change endpoint URLs to use new format
- [ ] Update method signatures to use `String` IDs
- [ ] Test all API calls

### Step 3: Update Views
- [ ] Replace UUID parameters with String
- [ ] Update NavigationLink destinations
- [ ] Update `@State` and `@Published` properties

### Step 4: Update Persistence (if any)
- [ ] Update Core Data/SwiftData models
- [ ] Update UserDefaults keys
- [ ] Migrate existing stored IDs

### Step 5: Testing
- [ ] Test profile loading
- [ ] Test profile updates
- [ ] Test navigation
- [ ] Test offline caching

---

## 🔄 Migration Examples

### Before (UUID):
```swift
struct BuyerProfile: Identifiable {
    let id: UUID
    // ...
}

// Usage
let buyer = BuyerProfile(id: UUID(), ...)
```

### After (Typed String ID):
```swift
struct BuyerProfile: Identifiable {
    let id: String  // "BYR-1699564234-A7K9M2"
    // ...
}

// Usage
let buyer = BuyerProfile(id: "BYR-1699564234-A7K9M2", ...)
```

---

## ✨ Benefits

1. **Type Safety**: ID prefix identifies resource type
2. **Better Debugging**: IDs are readable in logs
3. **URL Friendly**: Can be used directly in URLs
4. **No Conversion**: No UUID ↔ String conversion needed
5. **Consistent**: Same format across all platforms

---

## 📞 Support

If you encounter issues:
1. Check API response format matches models
2. Verify date decoding strategy (ISO8601)
3. Check for nil values in required fields
4. Enable verbose logging in APIClient

---

## Next Steps

1. Run the migration on backend first
2. Update one model at a time
3. Test thoroughly in development
4. Deploy to TestFlight for beta testing
