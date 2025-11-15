# iOS Features Implementation Guide

This document describes the iOS features to implement for improved media handling.

## 1. Image Caching with Kingfisher

### Installation
Add to your `Package.swift` or use SPM:
```swift
dependencies: [
    .package(url: "https://github.com/onevcat/Kingfisher.git", from: "8.0.0")
]
```

### Implementation

Create a new file: `Utilities/CachedMediaImage.swift`

```swift
import SwiftUI
import Kingfisher

struct CachedMediaImage: View {
    let media: MediaOut
    let size: MediaSize

    enum MediaSize {
        case thumbnail
        case medium
        case large
        case original

        var url: (MediaOut) -> String? {
            switch self {
            case .thumbnail: return { $0.thumbnailUrl }
            case .medium: return { $0.mediumUrl }
            case .large: return { $0.largeUrl }
            case .original: return { $0.originalUrl }
            }
        }
    }

    var body: some View {
        if let urlString = size.url(media), let url = URL(string: urlString) {
            KFImage(url)
                .placeholder {
                    ProgressView()
                }
                .retry(maxCount: 3, interval: .seconds(2))
                .cacheMemoryOnly() // Cache in memory
                .fade(duration: 0.25)
                .resizable()
                .aspectRatio(contentMode: .fill)
        } else {
            Image(systemName: "photo")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .foregroundColor(.gray)
        }
    }
}

// Clear cache helper
extension KingfisherManager {
    static func clearAllCache() {
        KingfisherManager.shared.cache.clearMemoryCache()
        KingfisherManager.shared.cache.clearDiskCache()
    }
}
```

### Usage
Replace your `AsyncImage` calls with:
```swift
CachedMediaImage(media: mediaItem, size: .thumbnail)
    .frame(width: 100, height: 100)
    .clipped()
```

## 2. Progressive Image Loading

Create `Components/ProgressiveMediaImage.swift`:

```swift
import SwiftUI
import Kingfisher

struct ProgressiveMediaImage: View {
    let media: MediaOut
    @State private var loadHighRes = false

    var body: some View {
        ZStack {
            // Load thumbnail first (fast)
            if let thumbUrl = media.thumbnailUrl, let url = URL(string: thumbUrl) {
                KFImage(url)
                    .placeholder { Color.gray.opacity(0.2) }
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .blur(radius: loadHighRes ? 0 : 2)
            }

            // Then load higher res
            if loadHighRes, let mediumUrl = media.mediumUrl ?? media.originalUrl,
               let url = URL(string: mediumUrl) {
                KFImage(url)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .transition(.opacity)
            }
        }
        .onAppear {
            // Delay high-res load
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                withAnimation {
                    loadHighRes = true
                }
            }
        }
    }
}
```

## 3. Batch Delete in MediaScraperView

Add to your `MediaScraperView.swift`:

```swift
// Add to state variables
@State private var selectedMediaIds: Set<Int> = []
@State private var isSelectionMode = false
@State private var isDeletingBatch = false

// Add batch delete function
private func batchDeleteMedia() {
    guard !selectedMediaIds.isEmpty else { return }

    isDeletingBatch = true

    Task {
        do {
            // Call batch delete endpoint
            let mediaIds = Array(selectedMediaIds)
            let response = try await container.mediaRepo.batchDeleteMedia(ids: mediaIds)

            await MainActor.run {
                // Remove deleted items from local state
                scrapedMedia.removeAll { selectedMediaIds.contains($0.id) }
                selectedMediaIds.removeAll()
                isSelectionMode = false
                isDeletingBatch = false

                // Show success message
                print("Batch deleted \(response.deletedCount) items")
            }
        } catch {
            await MainActor.run {
                isDeletingBatch = false
                print("Batch delete failed: \(error)")
            }
        }
    }
}

// Add to toolbar
.toolbar {
    if !scrapedMedia.isEmpty {
        ToolbarItem(placement: .navigationBarTrailing) {
            Button(isSelectionMode ? "Cancel" : "Select") {
                withAnimation {
                    isSelectionMode.toggle()
                    if !isSelectionMode {
                        selectedMediaIds.removeAll()
                    }
                }
            }
        }

        if isSelectionMode {
            ToolbarItem(placement: .bottomBar) {
                HStack {
                    Button("Select All") {
                        if selectedMediaIds.count == scrapedMedia.count {
                            selectedMediaIds.removeAll()
                        } else {
                            selectedMediaIds = Set(scrapedMedia.map { $0.id })
                        }
                    }

                    Spacer()

                    Button("Delete Selected (\(selectedMediaIds.count))") {
                        batchDeleteMedia()
                    }
                    .disabled(selectedMediaIds.isEmpty || isDeletingBatch)
                }
            }
        }
    }
}
```

## 4. Backend Batch Delete Repository Method

Add to your `Data/Repositories/MediaRepository.swift`:

```swift
func batchDeleteMedia(ids: [Int]) async throws -> BatchDeleteResponse {
    let url = baseURL.appendingPathComponent("/v1/media/batch/delete")

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    if let token = keychain.get("access_token") {
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }

    let body = ids
    request.httpBody = try JSONEncoder().encode(body)

    let (data, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw NetworkError.invalidResponse
    }

    return try JSONDecoder().decode(BatchDeleteResponse.self, from: data)
}

// Response model
public struct BatchDeleteResponse: Codable {
    public let deleted: [Int]
    public let deletedCount: Int
    public let failed: [FailedDeletion]
    public let failedCount: Int
    public let message: String

    public struct FailedDeletion: Codable {
        public let id: Int
        public let error: String
    }
}
```

## New Backend Endpoints Added

### 1. Batch Delete
```
POST /v1/media/batch/delete
Body: [1, 2, 3, 4, 5]  // Array of media IDs
Response: {
    "deleted": [1, 2, 3],
    "deleted_count": 3,
    "failed": [{"id": 4, "error": "Not found"}],
    "failed_count": 1,
    "message": "Successfully deleted 3 items"
}
```

### 2. Storage Analytics
```
GET /v1/media/analytics/storage?entity_type=community
Response: {
    "total_files": 150,
    "total_size_bytes": 45678912,
    "total_size_mb": 43.56,
    "total_size_gb": 0.04,
    "by_entity_and_type": [
        {
            "entity_type": "community",
            "media_type": "IMAGE",
            "count": 120,
            "total_size_mb": 38.5
        }
    ]
}
```

## Testing

### Test Batch Delete
```bash
curl -X POST http://localhost:8000/v1/media/batch/delete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[1, 2, 3]'
```

### Test Storage Analytics
```bash
curl http://localhost:8000/v1/media/analytics/storage \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Benefits

1. **Image Caching**:
   - Faster loading on repeat views
   - Reduced bandwidth usage
   - Better offline experience
   - Automatic cache management

2. **Progressive Loading**:
   - Instant thumbnail display
   - Smooth transition to high-res
   - Better perceived performance

3. **Batch Delete**:
   - Delete multiple items at once
   - Permission checks per item
   - Atomic database operations
   - Detailed error reporting

4. **Storage Analytics**:
   - Monitor storage usage
   - Plan capacity
   - Identify large files
   - Track by entity type

## Next Steps

After implementing these features:
1. Test with real media
2. Monitor cache size
3. Adjust image quality settings if needed
4. Add cache clearing option in settings
