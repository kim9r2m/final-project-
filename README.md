# final-project-

```mermaid
flowchart TD

    A[User Input]

    A --> B[Tab1: AI Helper]
    B --> B1[OpenAI ChatCompletion → Response]

    A --> C[Tab2: Color Helper]
    C --> C1[HF API analysis]
    C --> C2[Semantic dictionary matching]
    C --> C3[HSV palette generation]
    C --> C4[CSV download]

    A --> D[Tab3: Animal Pattern]
    D --> D1[Fetch external animal images]
    D --> D2[Extract palette (KMeans)]
    D --> D3[Generate pixel pattern]
    D --> D4[CSV download]

    A --> E[Tab4: Convert Image to Pattern]
    E --> E1[File upload]
    E --> E2[Extract palette]
    E --> E3[Render pixel pattern]
    E --> E4[CSV download]
