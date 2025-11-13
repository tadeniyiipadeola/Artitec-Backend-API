# SwiftUI Password Reset Implementation Guide

**Created:** November 12, 2024
**For:** Artitec iOS App

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [API Service](#api-service)
4. [View Models](#view-models)
5. [SwiftUI Views](#swiftui-views)
6. [Navigation Flow](#navigation-flow)
7. [Testing](#testing)
8. [Best Practices](#best-practices)

---

## 🎯 Overview

### User Flow

```
Login Screen
    ↓
"Forgot Password?" tap
    ↓
Forgot Password Screen
    ↓ (enter email)
Email Sent Confirmation
    ↓
User checks email
    ↓
Tap reset link (opens app or web)
    ↓
Reset Password Screen
    ↓ (enter new password)
Success → Navigate to Login
```

### Implementation Components

1. **ForgotPasswordView** - Email entry screen
2. **ResetPasswordView** - New password entry screen
3. **PasswordResetService** - API networking
4. **PasswordResetViewModel** - Business logic & state management

---

## 📁 File Structure

```
YourApp/
├── Services/
│   └── PasswordResetService.swift
├── ViewModels/
│   └── PasswordResetViewModel.swift
├── Views/
│   ├── Auth/
│   │   ├── LoginView.swift (modified)
│   │   ├── ForgotPasswordView.swift (new)
│   │   └── ResetPasswordView.swift (new)
│   └── Components/
│       └── PasswordStrengthIndicator.swift (optional)
└── Models/
    └── PasswordResetModels.swift
```

---

## 🌐 API Service

### PasswordResetService.swift

```swift
// Services/PasswordResetService.swift
import Foundation

enum PasswordResetError: LocalizedError {
    case invalidURL
    case invalidResponse
    case invalidToken
    case tokenExpired
    case weakPassword(String)
    case networkError(String)
    case serverError(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid request URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .invalidToken:
            return "Invalid or expired reset token"
        case .tokenExpired:
            return "This reset link has expired. Please request a new one."
        case .weakPassword(let message):
            return message
        case .networkError(let message):
            return "Network error: \(message)"
        case .serverError(let message):
            return message
        }
    }
}

struct ForgotPasswordRequest: Codable {
    let email: String
}

struct ForgotPasswordResponse: Codable {
    let message: String
}

struct ResetPasswordRequest: Codable {
    let token: String
    let newPassword: String

    enum CodingKeys: String, CodingKey {
        case token
        case newPassword = "new_password"
    }
}

struct ResetPasswordResponse: Codable {
    let message: String
    let userId: String?

    enum CodingKeys: String, CodingKey {
        case message
        case userId = "user_id"
    }
}

struct VerifyTokenRequest: Codable {
    let token: String
}

struct VerifyTokenResponse: Codable {
    let valid: Bool
    let message: String
    let expiresAt: String?
    let userEmail: String?

    enum CodingKeys: String, CodingKey {
        case valid, message
        case expiresAt = "expires_at"
        case userEmail = "user_email"
    }
}

class PasswordResetService {
    static let shared = PasswordResetService()

    private let baseURL: String

    private init() {
        // Get from your app configuration
        self.baseURL = AppConfig.apiBaseURL // e.g., "http://localhost:8000"
    }

    // MARK: - Request Password Reset

    func requestPasswordReset(email: String) async throws -> ForgotPasswordResponse {
        guard let url = URL(string: "\(baseURL)/v1/auth/forgot-password") else {
            throw PasswordResetError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ForgotPasswordRequest(email: email)
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw PasswordResetError.invalidResponse
        }

        if httpResponse.statusCode == 200 {
            let result = try JSONDecoder().decode(ForgotPasswordResponse.self, from: data)
            return result
        } else {
            let errorMessage = try? JSONDecoder().decode([String: String].self, from: data)
            throw PasswordResetError.serverError(errorMessage?["detail"] ?? "Unknown error")
        }
    }

    // MARK: - Verify Reset Token

    func verifyResetToken(_ token: String) async throws -> VerifyTokenResponse {
        guard let url = URL(string: "\(baseURL)/v1/auth/verify-reset-token") else {
            throw PasswordResetError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = VerifyTokenRequest(token: token)
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw PasswordResetError.invalidResponse
        }

        if httpResponse.statusCode == 200 {
            let result = try JSONDecoder().decode(VerifyTokenResponse.self, from: data)
            return result
        } else {
            throw PasswordResetError.invalidToken
        }
    }

    // MARK: - Reset Password

    func resetPassword(token: String, newPassword: String) async throws -> ResetPasswordResponse {
        guard let url = URL(string: "\(baseURL)/v1/auth/reset-password") else {
            throw PasswordResetError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ResetPasswordRequest(token: token, newPassword: newPassword)
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw PasswordResetError.invalidResponse
        }

        if httpResponse.statusCode == 200 {
            let result = try JSONDecoder().decode(ResetPasswordResponse.self, from: data)
            return result
        } else if httpResponse.statusCode == 400 {
            // Handle specific validation errors
            if let errorData = try? JSONDecoder().decode([String: String].self, from: data),
               let detail = errorData["detail"] {
                if detail.contains("expired") {
                    throw PasswordResetError.tokenExpired
                } else if detail.contains("Password") {
                    throw PasswordResetError.weakPassword(detail)
                } else {
                    throw PasswordResetError.serverError(detail)
                }
            }
            throw PasswordResetError.invalidToken
        } else {
            let errorMessage = try? JSONDecoder().decode([String: String].self, from: data)
            throw PasswordResetError.serverError(errorMessage?["detail"] ?? "Unknown error")
        }
    }
}

// MARK: - App Configuration (add to your existing config)

struct AppConfig {
    static let apiBaseURL: String = {
        #if DEBUG
        return "http://localhost:8000"
        #else
        return "https://api.artitec.com"
        #endif
    }()
}
```

---

## 🧠 View Models

### PasswordResetViewModel.swift

```swift
// ViewModels/PasswordResetViewModel.swift
import Foundation
import Combine

@MainActor
class ForgotPasswordViewModel: ObservableObject {
    @Published var email: String = ""
    @Published var isLoading: Bool = false
    @Published var showSuccess: Bool = false
    @Published var errorMessage: String?

    private let service = PasswordResetService.shared

    var isValidEmail: Bool {
        let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let emailPredicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
        return emailPredicate.evaluate(with: email)
    }

    var canSubmit: Bool {
        !email.isEmpty && isValidEmail && !isLoading
    }

    func requestPasswordReset() async {
        guard canSubmit else { return }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await service.requestPasswordReset(email: email)
            showSuccess = true
            print("✅ Password reset requested: \(response.message)")
        } catch let error as PasswordResetError {
            errorMessage = error.localizedDescription
        } catch {
            errorMessage = "An unexpected error occurred. Please try again."
        }

        isLoading = false
    }

    func reset() {
        email = ""
        showSuccess = false
        errorMessage = nil
    }
}

@MainActor
class ResetPasswordViewModel: ObservableObject {
    @Published var newPassword: String = ""
    @Published var confirmPassword: String = ""
    @Published var isLoading: Bool = false
    @Published var isVerifyingToken: Bool = true
    @Published var showSuccess: Bool = false
    @Published var errorMessage: String?
    @Published var tokenInfo: VerifyTokenResponse?

    let token: String
    private let service = PasswordResetService.shared

    init(token: String) {
        self.token = token
    }

    // Password validation
    var passwordValidation: [PasswordRequirement] {
        [
            PasswordRequirement(
                text: "At least 8 characters",
                isMet: newPassword.count >= 8
            ),
            PasswordRequirement(
                text: "Contains uppercase letter",
                isMet: newPassword.contains(where: { $0.isUppercase })
            ),
            PasswordRequirement(
                text: "Contains lowercase letter",
                isMet: newPassword.contains(where: { $0.isLowercase })
            ),
            PasswordRequirement(
                text: "Contains number",
                isMet: newPassword.contains(where: { $0.isNumber })
            ),
            PasswordRequirement(
                text: "Passwords match",
                isMet: !newPassword.isEmpty && newPassword == confirmPassword
            )
        ]
    }

    var isPasswordValid: Bool {
        passwordValidation.allSatisfy { $0.isMet }
    }

    var canSubmit: Bool {
        isPasswordValid && !isLoading
    }

    // Verify token on init
    func verifyToken() async {
        isVerifyingToken = true
        errorMessage = nil

        do {
            let response = try await service.verifyResetToken(token)
            if response.valid {
                tokenInfo = response
            } else {
                errorMessage = response.message
            }
        } catch let error as PasswordResetError {
            errorMessage = error.localizedDescription
        } catch {
            errorMessage = "Failed to verify reset link. Please try again."
        }

        isVerifyingToken = false
    }

    func resetPassword() async {
        guard canSubmit else { return }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await service.resetPassword(token: token, newPassword: newPassword)
            showSuccess = true
            print("✅ Password reset successful: \(response.message)")
        } catch let error as PasswordResetError {
            errorMessage = error.localizedDescription
        } catch {
            errorMessage = "An unexpected error occurred. Please try again."
        }

        isLoading = false
    }
}

struct PasswordRequirement {
    let text: String
    let isMet: Bool
}
```

---

## 🎨 SwiftUI Views

### 1. ForgotPasswordView.swift

```swift
// Views/Auth/ForgotPasswordView.swift
import SwiftUI

struct ForgotPasswordView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = ForgotPasswordViewModel()

    var body: some View {
        NavigationView {
            ZStack {
                // Background gradient
                LinearGradient(
                    colors: [Color(hex: "D4AF37"), Color(hex: "C5A028")],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Content area
                    ScrollView {
                        VStack(spacing: 24) {
                            // Header
                            VStack(spacing: 12) {
                                Image(systemName: "lock.rotation")
                                    .font(.system(size: 60))
                                    .foregroundColor(.white)

                                Text("Forgot Password?")
                                    .font(.title)
                                    .fontWeight(.bold)
                                    .foregroundColor(.white)

                                Text("Enter your email address and we'll send you a link to reset your password.")
                                    .font(.body)
                                    .foregroundColor(.white.opacity(0.9))
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal)
                            }
                            .padding(.top, 40)
                            .padding(.bottom, 20)

                            // Form card
                            VStack(spacing: 20) {
                                // Email input
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Email Address")
                                        .font(.subheadline)
                                        .fontWeight(.medium)
                                        .foregroundColor(.secondary)

                                    HStack {
                                        Image(systemName: "envelope")
                                            .foregroundColor(.secondary)

                                        TextField("your@email.com", text: $viewModel.email)
                                            .textContentType(.emailAddress)
                                            .autocapitalization(.none)
                                            .keyboardType(.emailAddress)
                                            .disabled(viewModel.isLoading)
                                    }
                                    .padding()
                                    .background(Color(.systemGray6))
                                    .cornerRadius(12)

                                    if !viewModel.email.isEmpty && !viewModel.isValidEmail {
                                        Label("Please enter a valid email address", systemImage: "exclamationmark.circle")
                                            .font(.caption)
                                            .foregroundColor(.red)
                                    }
                                }

                                // Error message
                                if let errorMessage = viewModel.errorMessage {
                                    HStack {
                                        Image(systemName: "exclamationmark.triangle.fill")
                                        Text(errorMessage)
                                        Spacer()
                                    }
                                    .font(.caption)
                                    .foregroundColor(.red)
                                    .padding()
                                    .background(Color.red.opacity(0.1))
                                    .cornerRadius(8)
                                }

                                // Submit button
                                Button(action: {
                                    Task {
                                        await viewModel.requestPasswordReset()
                                    }
                                }) {
                                    HStack {
                                        if viewModel.isLoading {
                                            ProgressView()
                                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                        } else {
                                            Text("Send Reset Link")
                                                .fontWeight(.semibold)
                                        }
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(
                                        viewModel.canSubmit ?
                                        LinearGradient(
                                            colors: [Color(hex: "D4AF37"), Color(hex: "C5A028")],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        ) :
                                        LinearGradient(
                                            colors: [Color.gray, Color.gray],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        )
                                    )
                                    .foregroundColor(.white)
                                    .cornerRadius(12)
                                }
                                .disabled(!viewModel.canSubmit)

                                // Back to login
                                Button(action: {
                                    dismiss()
                                }) {
                                    HStack {
                                        Image(systemName: "chevron.left")
                                        Text("Back to Login")
                                    }
                                    .font(.subheadline)
                                    .foregroundColor(Color(hex: "D4AF37"))
                                }
                                .disabled(viewModel.isLoading)
                            }
                            .padding(24)
                            .background(Color(.systemBackground))
                            .cornerRadius(20)
                            .shadow(color: .black.opacity(0.1), radius: 10, y: 5)
                            .padding(.horizontal)
                        }
                    }
                }
            }
            .navigationBarHidden(true)
        }
        .alert("Check Your Email", isPresented: $viewModel.showSuccess) {
            Button("OK") {
                dismiss()
            }
        } message: {
            Text("If an account exists with that email, we've sent you a password reset link. Please check your inbox and spam folder.")
        }
    }
}

// MARK: - Preview

struct ForgotPasswordView_Previews: PreviewProvider {
    static var previews: some View {
        ForgotPasswordView()
    }
}
```

### 2. ResetPasswordView.swift

```swift
// Views/Auth/ResetPasswordView.swift
import SwiftUI

struct ResetPasswordView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel: ResetPasswordViewModel
    @State private var showPassword = false
    @State private var showConfirmPassword = false

    init(token: String) {
        _viewModel = StateObject(wrappedValue: ResetPasswordViewModel(token: token))
    }

    var body: some View {
        NavigationView {
            ZStack {
                // Background
                LinearGradient(
                    colors: [Color(hex: "D4AF37"), Color(hex: "C5A028")],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                if viewModel.isVerifyingToken {
                    // Loading state
                    VStack(spacing: 20) {
                        ProgressView()
                            .scaleEffect(1.5)
                            .tint(.white)
                        Text("Verifying reset link...")
                            .foregroundColor(.white)
                            .font(.headline)
                    }
                } else if viewModel.errorMessage != nil && viewModel.tokenInfo == nil {
                    // Invalid token state
                    invalidTokenView
                } else {
                    // Valid token - show reset form
                    resetFormView
                }
            }
            .navigationBarHidden(true)
            .task {
                await viewModel.verifyToken()
            }
        }
        .alert("Password Reset Successful", isPresented: $viewModel.showSuccess) {
            Button("Login Now") {
                dismiss()
                // Navigate to login
            }
        } message: {
            Text("Your password has been reset successfully. You can now log in with your new password.")
        }
    }

    // MARK: - Invalid Token View

    private var invalidTokenView: some View {
        VStack(spacing: 24) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 60))
                .foregroundColor(.white)

            Text("Invalid Reset Link")
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(.white)

            Text(viewModel.errorMessage ?? "This reset link is invalid or has expired.")
                .font(.body)
                .foregroundColor(.white.opacity(0.9))
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Button(action: {
                dismiss()
            }) {
                Text("Back to Login")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.white)
                    .foregroundColor(Color(hex: "D4AF37"))
                    .cornerRadius(12)
            }
            .padding(.horizontal, 40)
        }
    }

    // MARK: - Reset Form View

    private var resetFormView: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header
                VStack(spacing: 12) {
                    Image(systemName: "lock.shield")
                        .font(.system(size: 60))
                        .foregroundColor(.white)

                    Text("Reset Password")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.white)

                    if let userEmail = viewModel.tokenInfo?.userEmail {
                        Text("For: \(userEmail)")
                            .font(.subheadline)
                            .foregroundColor(.white.opacity(0.9))
                    }
                }
                .padding(.top, 40)
                .padding(.bottom, 20)

                // Form card
                VStack(spacing: 20) {
                    // New Password
                    VStack(alignment: .leading, spacing: 8) {
                        Text("New Password")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)

                        HStack {
                            Image(systemName: "lock")
                                .foregroundColor(.secondary)

                            if showPassword {
                                TextField("Enter new password", text: $viewModel.newPassword)
                            } else {
                                SecureField("Enter new password", text: $viewModel.newPassword)
                            }

                            Button(action: { showPassword.toggle() }) {
                                Image(systemName: showPassword ? "eye.slash" : "eye")
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }

                    // Confirm Password
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Confirm Password")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)

                        HStack {
                            Image(systemName: "lock")
                                .foregroundColor(.secondary)

                            if showConfirmPassword {
                                TextField("Confirm new password", text: $viewModel.confirmPassword)
                            } else {
                                SecureField("Confirm new password", text: $viewModel.confirmPassword)
                            }

                            Button(action: { showConfirmPassword.toggle() }) {
                                Image(systemName: showConfirmPassword ? "eye.slash" : "eye")
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }

                    // Password requirements
                    if !viewModel.newPassword.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Password Requirements")
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(.secondary)

                            ForEach(viewModel.passwordValidation, id: \.text) { requirement in
                                HStack(spacing: 8) {
                                    Image(systemName: requirement.isMet ? "checkmark.circle.fill" : "circle")
                                        .foregroundColor(requirement.isMet ? .green : .secondary)
                                        .font(.caption)

                                    Text(requirement.text)
                                        .font(.caption)
                                        .foregroundColor(requirement.isMet ? .primary : .secondary)
                                }
                            }
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }

                    // Error message
                    if let errorMessage = viewModel.errorMessage {
                        HStack {
                            Image(systemName: "exclamationmark.triangle.fill")
                            Text(errorMessage)
                            Spacer()
                        }
                        .font(.caption)
                        .foregroundColor(.red)
                        .padding()
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(8)
                    }

                    // Submit button
                    Button(action: {
                        Task {
                            await viewModel.resetPassword()
                        }
                    }) {
                        HStack {
                            if viewModel.isLoading {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            } else {
                                Text("Reset Password")
                                    .fontWeight(.semibold)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            viewModel.canSubmit ?
                            LinearGradient(
                                colors: [Color(hex: "D4AF37"), Color(hex: "C5A028")],
                                startPoint: .leading,
                                endPoint: .trailing
                            ) :
                            LinearGradient(
                                colors: [Color.gray, Color.gray],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .foregroundColor(.white)
                        .cornerRadius(12)
                    }
                    .disabled(!viewModel.canSubmit)

                    // Back to login
                    Button(action: {
                        dismiss()
                    }) {
                        HStack {
                            Image(systemName: "chevron.left")
                            Text("Back to Login")
                        }
                        .font(.subheadline)
                        .foregroundColor(Color(hex: "D4AF37"))
                    }
                    .disabled(viewModel.isLoading)
                }
                .padding(24)
                .background(Color(.systemBackground))
                .cornerRadius(20)
                .shadow(color: .black.opacity(0.1), radius: 10, y: 5)
                .padding(.horizontal)
            }
        }
    }
}

// MARK: - Preview

struct ResetPasswordView_Previews: PreviewProvider {
    static var previews: some View {
        ResetPasswordView(token: "sample-token-123")
    }
}
```

### 3. Update LoginView.swift

```swift
// Add to your existing LoginView.swift

struct LoginView: View {
    // ... existing properties
    @State private var showForgotPassword = false

    var body: some View {
        // ... existing content

        // Add this after the login button:
        Button(action: {
            showForgotPassword = true
        }) {
            Text("Forgot Password?")
                .font(.subheadline)
                .foregroundColor(Color(hex: "D4AF37"))
        }
        .padding(.top, 8)
        .sheet(isPresented: $showForgotPassword) {
            ForgotPasswordView()
        }
    }
}
```

---

## 🔗 Navigation & Deep Linking

### Handle Reset Links from Email

```swift
// In your App.swift or main coordinator

import SwiftUI

@main
struct ArtitecApp: App {
    @StateObject private var coordinator = AppCoordinator()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(coordinator)
                .onOpenURL { url in
                    handleDeepLink(url)
                }
        }
    }

    private func handleDeepLink(_ url: URL) {
        // Example URL: artitec://reset-password?token=abc123
        // Or web URL: https://artitec.com/reset-password?token=abc123

        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true),
              let token = components.queryItems?.first(where: { $0.name == "token" })?.value
        else {
            print("❌ Invalid reset link")
            return
        }

        // Navigate to reset password screen
        coordinator.showResetPassword(token: token)
    }
}

// App Coordinator for navigation
class AppCoordinator: ObservableObject {
    @Published var showResetPassword = false
    @Published var resetToken: String?

    func showResetPassword(token: String) {
        self.resetToken = token
        self.showResetPassword = true
    }
}

// In ContentView or your main navigation:
struct ContentView: View {
    @EnvironmentObject var coordinator: AppCoordinator

    var body: some View {
        // Your main content
        NavigationView {
            // ...
        }
        .sheet(isPresented: $coordinator.showResetPassword) {
            if let token = coordinator.resetToken {
                ResetPasswordView(token: token)
            }
        }
    }
}
```

### Configure URL Scheme

**In Xcode:**
1. Select your project → Target → Info
2. URL Types → Add (+)
3. URL Schemes: `artitec`
4. Identifier: `com.artitec.app`

**In Info.plist:**
```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>artitec</string>
        </array>
        <key>CFBundleURLName</key>
        <string>com.artitec.app</string>
    </dict>
</array>
```

### Update Backend Email Template

Make sure your email service sends the correct iOS deep link:

```python
# In src/email_service.py, update reset_url generation:

def send_password_reset_email(self, to_email: str, reset_token: str, user_name: Optional[str] = None):
    # For iOS app deep linking:
    reset_url = f"artitec://reset-password?token={reset_token}"

    # Or for universal links (requires setup):
    # reset_url = f"https://artitec.com/reset-password?token={reset_token}"

    # ...
```

---

## 🎨 Helper Extensions

### Color Extension

```swift
// Extensions/Color+Hex.swift
import SwiftUI

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
```

---

## ✅ Testing Checklist

### Manual Testing

- [ ] **Forgot Password Flow**
  - [ ] Enter valid email → Success message shown
  - [ ] Enter invalid email format → Validation error shown
  - [ ] Email field validation works
  - [ ] Loading state displays correctly
  - [ ] Can dismiss view after success

- [ ] **Email Reception**
  - [ ] Email received (check inbox and spam)
  - [ ] Email displays correctly on mobile
  - [ ] Reset link is clickable
  - [ ] Link opens app (deep link works)

- [ ] **Reset Password Flow**
  - [ ] Valid token → Form shown
  - [ ] Invalid token → Error shown
  - [ ] Expired token → Appropriate error
  - [ ] Password requirements display
  - [ ] Real-time validation works
  - [ ] Show/hide password works
  - [ ] Success redirects to login

- [ ] **Edge Cases**
  - [ ] Network offline → Error handled gracefully
  - [ ] Server error → User-friendly message
  - [ ] Token used twice → Error shown
  - [ ] Navigate away and back → State preserved

### Unit Testing

```swift
// Tests/PasswordResetViewModelTests.swift
import XCTest
@testable import YourApp

class ForgotPasswordViewModelTests: XCTestCase {

    func testEmailValidation() {
        let viewModel = ForgotPasswordViewModel()

        viewModel.email = "invalid"
        XCTAssertFalse(viewModel.isValidEmail)

        viewModel.email = "valid@email.com"
        XCTAssertTrue(viewModel.isValidEmail)
    }

    func testCanSubmitRequiresValidEmail() {
        let viewModel = ForgotPasswordViewModel()

        viewModel.email = ""
        XCTAssertFalse(viewModel.canSubmit)

        viewModel.email = "invalid"
        XCTAssertFalse(viewModel.canSubmit)

        viewModel.email = "valid@email.com"
        XCTAssertTrue(viewModel.canSubmit)
    }
}

class ResetPasswordViewModelTests: XCTestCase {

    func testPasswordValidation() {
        let viewModel = ResetPasswordViewModel(token: "test-token")

        // Too short
        viewModel.newPassword = "Pass1"
        XCTAssertFalse(viewModel.isPasswordValid)

        // No uppercase
        viewModel.newPassword = "password123"
        XCTAssertFalse(viewModel.isPasswordValid)

        // No lowercase
        viewModel.newPassword = "PASSWORD123"
        XCTAssertFalse(viewModel.isPasswordValid)

        // No number
        viewModel.newPassword = "PasswordOnly"
        XCTAssertFalse(viewModel.isPasswordValid)

        // Valid password but no confirmation
        viewModel.newPassword = "Password123"
        XCTAssertFalse(viewModel.isPasswordValid)

        // Valid password with matching confirmation
        viewModel.newPassword = "Password123"
        viewModel.confirmPassword = "Password123"
        XCTAssertTrue(viewModel.isPasswordValid)
    }
}
```

---

## 🎯 Best Practices

### 1. Security

✅ **Never store passwords** in UserDefaults or anywhere else
✅ **Use HTTPS** in production (enforce with App Transport Security)
✅ **Validate on both** client and server
✅ **Clear password fields** after submission
✅ **Use SecureField** for password input
✅ **Implement biometric auth** for returning users (Face ID/Touch ID)

### 2. User Experience

✅ **Real-time validation** with clear error messages
✅ **Loading states** for all async operations
✅ **Password visibility toggle** for user convenience
✅ **Password strength indicator** (visual feedback)
✅ **Clear success/error messaging**
✅ **Haptic feedback** for errors and success
✅ **Accessibility** labels for VoiceOver

### 3. Error Handling

```swift
// Always provide user-friendly error messages
enum UserFriendlyError: LocalizedError {
    case networkOffline
    case serverError
    case invalidInput

    var errorDescription: String? {
        switch self {
        case .networkOffline:
            return "No internet connection. Please check your network and try again."
        case .serverError:
            return "Something went wrong on our end. Please try again later."
        case .invalidInput:
            return "Please check your input and try again."
        }
    }
}
```

### 4. Accessibility

```swift
// Add accessibility labels
TextField("Email", text: $email)
    .accessibilityLabel("Email address")
    .accessibilityHint("Enter your email to receive a password reset link")

Button("Reset Password") { }
    .accessibilityLabel("Reset password button")
    .accessibilityHint("Tap to submit your new password")
```

---

## 📋 Summary

Your SwiftUI app now has a complete password reset flow:

✅ **ForgotPasswordView** - Email entry with validation
✅ **ResetPasswordView** - New password entry with strength validation
✅ **PasswordResetService** - API networking layer
✅ **ViewModels** - State management and business logic
✅ **Deep linking** - Handle reset links from email
✅ **Error handling** - Comprehensive error states
✅ **Accessibility** - VoiceOver support
✅ **Testing** - Unit test examples

**Next Steps:**
1. Add these files to your Xcode project
2. Test the forgot password flow
3. Configure deep linking
4. Test with real emails
5. Add analytics tracking (optional)
6. Implement password strength indicator UI (optional)

---

**Last Updated:** November 12, 2024
**Status:** ✅ Ready for Implementation
