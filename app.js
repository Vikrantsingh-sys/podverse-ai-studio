
document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.querySelector('input[type="file"]');
  const urlInput = document.querySelector('input[type="url"]');
  const button = document.querySelector("button");
  const status = document.getElementById("status");

  button.onclick = () => {
    const file = fileInput.files[0];
    const url = urlInput.value.trim();
    const platforms = [...document.querySelectorAll(
      '.platform input:checked'
    )].map(x => x.value);

    if (!file && !url) {
      status.textContent = "Please upload a video or enter a video link.";
      return;
    }

    if (!platforms.length) {
      status.textContent = "Please select at least one platform.";
      return;
    }

    if (file && file.size > 500 * 1024 * 1024) {
      status.textContent = "Please select a video smaller than 500 MB.";
      return;
    }

    status.textContent = file
      ? `Video selected: ${file.name}. Platform settings saved.`
      : "Link received. Direct video processing is not connected yet.";

    console.log("Selected platforms:", platforms);
  };
});
