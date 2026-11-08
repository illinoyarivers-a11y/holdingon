const form = document.querySelector("#convert-form");
const input = document.querySelector("#ao3-url");
const button = document.querySelector("#convert-button");
const buttonLabel = document.querySelector(".button-label");
const statusBox = document.querySelector("#status");
const downloadLink = document.querySelector("#download-link");

function showStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
  statusBox.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  downloadLink.hidden = true;
  statusBox.hidden = true;
  button.disabled = true;
  buttonLabel.textContent = "Converting…";
  showStatus("Fetching the AO3 work and building your EPUB. Larger works may take a little while.");

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: input.value.trim() })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Conversion failed.");

    showStatus(result.message || "Your EPUB is ready.");
    downloadLink.href = result.download_url;
    downloadLink.download = result.filename;
    downloadLink.hidden = false;
  } catch (error) {
    showStatus(error.message || "Something went wrong. Please try again.", true);
  } finally {
    button.disabled = false;
    buttonLabel.textContent = "Convert to EPUB";
  }
});
