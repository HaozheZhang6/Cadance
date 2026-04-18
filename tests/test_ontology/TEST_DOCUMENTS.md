# Real-World Test Documents for Ontology Extractors

Documents sourced for testing extractor functionality with real engineering data.

## 1. Component Datasheets (DatasheetExtractor)

| Document | Source | URL | Entities |
|----------|--------|-----|----------|
| LM317 Voltage Regulator | Texas Instruments | [PDF](https://www.ti.com/lit/ds/symlink/lm317.pdf) | Part numbers, voltage/current specs, packages |
| OP27 Op-Amp | Analog Devices | [PDF](https://www.analog.com/media/en/technical-documentation/data-sheets/op27.pdf) | Electrical specs, performance characteristics |
| DSBC Pneumatic Cylinders | Festo | [PDF](https://ftp.festo.com/Public/PNEUMATIC/SOFTWARE_SERVICE/Documentation/2018/EN/DSBC_EN.PDF) | Bore sizes, pressure ratings, ISO 15552 |
| Tapered Roller Bearings | Timken | [PDF](https://www.timken.com/wp-content/uploads/2016/10/Timken-Tapered-Roller-Bearing-Catalog.pdf) | Load ratings, dimensions, bore diameters |
| External Gear Pumps | Bosch Rexroth | [PDF](https://docs.rs-online.com/f0b2/0900766b812c44d2.pdf) | Flow rates, pressure ratings |

## 2. Engineering Standards (StandardExtractor)

| Document | Source | URL | Entities |
|----------|--------|-----|----------|
| B31.3 Process Piping Guide | LANL/ASME | [PDF](https://engstandards.lanl.gov/esm/pressure_safety/Section%20REF-3-R0.pdf) | Piping requirements, materials |
| A36 Carbon Structural Steel | ASTM | [PDF](https://pppars.com/wp-content/uploads/2020/12/ASTM-A-36.A-36M-%E2%80%93-05.pdf) | Chemical composition, mechanical properties |
| Good Standardization Practices | ISO | [PDF](https://www.iso.org/files/live/sites/isoorg/files/store/en/PUB100440.pdf) | Standardization methodology |

## 3. FMEA Documents (FailureModeExtractor)

| Document | Source | URL | Entities |
|----------|--------|-----|----------|
| FMEA Ranking Tables | AIAG | [PDF](https://elsmar.com/pdf_files/FMEA%20and%20Reliability%20Analysis/AIAG%20FMEA-Ranking-Tables.pdf) | Severity/occurrence/detection scales |
| DFMEA Example | Elsmar/Xfmea | [PDF](https://elsmar.com/pdf_files/FMEA%20and%20Reliability%20Analysis/dfmea_example.pdf) | Failure modes, causes, effects, RPN |
| FMEA Feasibility Study | NASA | [PDF](https://ntrs.nasa.gov/api/citations/20130013157/downloads/20130013157.pdf) | Aerospace failure modes library |
| FMECA Guide | Aerospace Corp | [PDF](https://s3vi.ndc.nasa.gov/ssri-kb/static/resources/TOR2009-8591-13.pdf) | FMECA methodology, aerospace examples |
| Fault Tree Handbook | NASA | [PDF](https://www.mwftr.com/CS2/Fault%20Tree%20Handbook_NASA.pdf) | FTA/FMEA for pressure tanks, propulsion |

## 4. Technical Manuals (DocumentExtractor)

| Document | Source | URL | Entities |
|----------|--------|-----|----------|
| DFM Guidelines | UNM | [PDF](https://www.unm.edu/~bgreen/ME101/dfm.pdf) | Manufacturing design rules |
| DFM Examples | UF | [PDF](https://web.mae.ufl.edu/designlab/Lab%20Assignments/EML2322L%20Design%20for%20Manufacturing%20Examples.pdf) | Milling, lathe, sheetmetal rules |
| Stainless Steel Design Guide | Nickel Institute | [PDF](https://nickelinstitute.org/media/1667/designguidelinesfortheselectionanduseofstainlesssteels_9014_.pdf) | Material selection, corrosion |
| 304/304L Data Sheet | Rolled Alloys | [PDF](https://www.rolledalloys.com/wp-content/uploads/304-304L_stainless-steel-data-sheet-rolled-alloys.pdf) | Chemical composition, properties |

## Recommended Test Cases

1. **TI LM317** - Well-structured tables, clear specs
2. **AIAG FMEA Tables** - Standard severity/occurrence/detection scales
3. **NASA FMEA Study** - Real aerospace failure modes with causes
4. **Festo DSBC** - Structured mechanical specs with ordering codes
5. **Timken Bearings** - Comprehensive dimensional/load data

## Usage

```python
# Download test document
import urllib.request
url = "https://www.ti.com/lit/ds/symlink/lm317.pdf"
urllib.request.urlretrieve(url, "lm317.pdf")

# Extract text (requires pdfplumber or similar)
import pdfplumber
with pdfplumber.open("lm317.pdf") as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)

# Run extractor
from src.ontology.extractors import DatasheetExtractor
extractor = DatasheetExtractor(llm_client)
result = await extractor.extract(text, "lm317.pdf", ConfidenceSource.DATASHEET)
```

## Notes

- All documents verified accessible as of Feb 2026
- PDFs preferred for consistent text extraction
- Some standards are archived versions (check currency for production use)
