plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.aiassistanthealthcare.firetv"
    // compileSdk is a build-time-only setting (not locked by D3, which fixes
    // only minSdk/targetSdk). Raised to 35 because androidx.tv:tv-foundation
    // and androidx.tv:tv-material (and their transitive Compose deps) declare
    // an AAR metadata minimum of compileSdk 35 — discovered via build failure,
    // not a design choice. It does not affect device compatibility (minSdk)
    // or runtime behavior opt-in (targetSdk).
    compileSdk = 35

    defaultConfig {
        applicationId = "com.aiassistanthealthcare.firetv"
        // Locked per ARCHITECTURE_MVP_PLAN.md D3 — do not change without approval.
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0-p1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))

    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")

    // Compose for TV — P2 will exercise focus/D-pad behaviour from these.
    implementation("androidx.tv:tv-foundation:1.0.0")
    implementation("androidx.tv:tv-material:1.1.0")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
