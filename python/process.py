import json
import re

def parse_age(age_text: str) -> float | None:
    """Parse AgeRange text to numeric age value.

    Rules:
    - lowercase
    - remove: about, younger than, probably
    - convert a.d. -> +
    - if hyphen: average numbers on both sides
    - convert numbers followed by 'ma' into millions
    """

    if not age_text or not isinstance(age_text, str):
        return None

    # normalize
    txt = age_text.lower().strip()

    # remove unwanted words
    for word in ["about", "younger than", "probably", ",", "age"]:
        txt = txt.replace(word, "")

    txt = txt.replace("a.d.", "+")

    # collapse and strip whitespace
    txt = re.sub(r"\s+", " ", txt).strip()

    # --- HANDLE MA VALUES ---
    # any number followed by "ma" → convert to millions
    def ma_to_number(s):
        num = float(s)
        return num * 1_000_000

    # --- HANDLE "TO" AVERAGING ---
    # e.g., "400 to 750 yr" → extract 400 and 750, average → "575 yr"
    if " to " in txt:
        left_txt, right_txt = txt.split(" to ", 1)

        # extract numbers
        left_nums = re.findall(r"[+-]?\d*\.?\d+", left_txt)
        right_nums = re.findall(r"[+-]?\d*\.?\d+", right_txt)

        if left_nums and right_nums:
            avg_val = (float(left_nums[0]) + float(right_nums[0])) / 2

            # keep surrounding non-numeric text
            left_suffix = re.sub(r"[+-]?\d*\.?\d+", "", left_txt).strip()
            right_suffix = re.sub(r"[+-]?\d*\.?\d+", "", right_txt).strip()

            # reconstruct text with averaged number
            reconstructed = f"{avg_val} {left_suffix} {right_suffix}".strip()

            txt = reconstructed

    # --- HANDLE HYPHENS ---
    hy = re.split(r"\s*-\s*", txt)
    if len(hy) == 2:
        left, right = hy

        # extract numeric values
        nums_left = re.findall(r"[+-]?\d*\.?\d+", left)
        nums_right = re.findall(r"[+-]?\d*\.?\d+", right)

        if nums_left and nums_right:
            avg = (float(nums_left[0]) + float(nums_right[0])) / 2

            # get text after the numbers
            left_suffix = re.sub(r"[+-]?\d*\.?\d+", "", left).strip()
            right_suffix = re.sub(r"[+-]?\d*\.?\d+", "", right).strip()

            # merge suffix text (avoids duplicates)
            suffix = (left_suffix + " " + right_suffix).strip()

            # rebuild the string: "avg suffix"
            txt = f"{avg} {suffix}".strip()

    # --- HANDLE MA (single or range) BUT DO NOT RETURN YET ---
    # convert "x ma" to number, and leave in txt as plain float for later rules
    ma_match = re.search(r"([+-]?\d*\.?\d+)\s*ma", txt)
    if ma_match:
        val = float(ma_match.group(1)) * 1_000_000
        txt = str(val)   # replace entire text with numeric value so year logic applies

    # --- SINGLE NUMBER (after MA cleanup) ---
    single = re.findall(r"[+-]?\d*\.?\d+", txt)
    if not single:
        return None

    val = float(single[0])

    # --- APPLY YEAR CONVERSION RULES ---
    # If original text had NO '+', treat as years ago:
    #  → make negative → then add 2000
    if "+" not in txt:
        val = - abs(val)
        if val > -80000:
            val = 2000 - abs(val)

    return int(val)

def process_age_field(input_path: str, output_path: str):
    """Reads GeoJSON and adds Age field parsed from AgeRange."""
    with open(input_path, "r") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        age_range = props.get("AgeRange")
        props["Age"] = parse_age(age_range)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)



process_age_field(
    "/Users/kanoalindiwe/Downloads/age/HawaiiStateGeologicMap_GeoJSON/MapUnitPolys.json",
    "/Users/kanoalindiwe/Downloads/age/HawaiiStateGeologicMap_GeoJSON/MapUnitPolys_output.json"
)