import io
import re

with open("src/App.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix default states
content = content.replace("const [rDias, setRDias] = useState(4)", "const [rDias, setRDias] = useState(28)")
content = content.replace("const [rCobertura, setRCobertura] = useState(4)", "const [rCobertura, setRCobertura] = useState(2)")

# 2. Fix FilterSelect options for rDias
dias_options_old = "options={[28, 56, 84, 112, 182, 365].map(v => ({ value: String(v), label: `${v} d\\u00edas` }))} />"
# Wait, let's use regex to replace the options array safely
content = re.sub(
    r'options=\{\[28,\s*56,\s*84,\s*112,\s*182,\s*365\]\.map\(v => \(\{ value: String\(v\), label: `\$\{v\} d[^\`]+` \}\)\)\} />',
    r'options={[7, 14, 21, 28, 35, 42, 49, 56, 84, 112, 182, 365].map(v => ({ value: String(v), label: `${v} días` }))} />',
    content
)

# 3. Fix FilterSelect options for rCobertura
content = re.sub(
    r'options=\{\[4,\s*8,\s*12,\s*16\]\.map\(v => \(\{ value: String\(v\), label: `\$\{v\} semanas` \}\)\)\} />',
    r'options={[2, 4, 6, 8, 12, 16].map(v => ({ value: String(v), label: `${v} semanas` }))} />',
    content
)

with open("src/App.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Reposición options fixed in App.tsx")
