from pytsg import parse_tsg
import matplotlib.pyplot as plt

folder = r"C:\Users\Dulya\Downloads\05GJD001\8a294cfc-68df-4f03-995b-c5fd0d47ab0"

# read_cras_file=True would also load the cras (possible classification) data,
# but that file decompresses to ~9.3 GB in memory and pytsg's own error handling
# for that failure is buggy (references `numpy` instead of `np`) - leave this
# off for now and revisit separately once we know it's needed.
data = parse_tsg.read_package(folder, read_cras_file=False)

# --- 1. See what shape the spectra actually is (confirm before plotting) ---
print("nir spectra shape:", data.nir.spectra.shape)
print("nir wavelength shape:", data.nir.wavelength.shape)

# --- 2. See the per-sample metadata columns (depth info lives here) ---
print("\nsampleheaders columns:", data.nir.sampleheaders.columns.tolist())
print(data.nir.sampleheaders.head())

# --- 3. See the interpreted mineral/trait values ---
print("\nscalars columns:", data.nir.scalars.columns.tolist())
print(data.nir.scalars.head())

# --- 4. Plot the first 10 spectra against wavelength ---
plt.plot(data.nir.wavelength, data.nir.spectra[0:10, :].T)
plt.xlabel("Wavelength (nm)")
plt.ylabel("Reflectance")
plt.title("05GJD001 — first 10 NIR/SWIR samples")
plt.savefig("nir_spectra_preview.png", dpi=120)
plt.show()

# --- 5. Same for TIR ---
if data.tir is not None:
    plt.plot(data.tir.wavelength, data.tir.spectra[0:10, :].T)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title("05GJD001 — first 10 TIR samples")
    plt.show()
