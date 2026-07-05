# R8/ProGuard rules for the release build (isMinifyEnabled + shrinkResources = true).
# Hilt, Room, and Compose ship their own consumer rules; app-specific keeps go here.

# Keep the domain model + pack DTOs intact (they cross the persistence / share-pack boundary and are
# referenced by name in JSON packs — defensive, so R8 can never rename a field a pack relies on).
-keep class com.speechangel.core.model.** { *; }
-keep class com.speechangel.data.pack.** { *; }

# Enum valueOf/entries reflection (DeviceAction.fromId, VoiceCondition, backend enums).
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# Foreground service + boot receiver are entry points referenced from the manifest.
-keep class com.speechangel.app.service.** { *; }
