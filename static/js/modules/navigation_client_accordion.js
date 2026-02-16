const groupButtons = Array.from(
  document.querySelectorAll('button[data-collapse-group="client-nav"][data-collapse-toggle]')
);

if (groupButtons.length > 0) {
  groupButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.getAttribute("data-collapse-toggle");
      const targetPanel = document.getElementById(targetId);
      if (!targetPanel) return;

      const targetWillOpen = targetPanel.classList.contains("hidden");
      if (!targetWillOpen) return;

      groupButtons.forEach((otherButton) => {
        if (otherButton === button) return;

        const otherId = otherButton.getAttribute("data-collapse-toggle");
        const otherPanel = document.getElementById(otherId);
        if (!otherPanel) return;

        otherPanel.classList.add("hidden");
      });
    });
  });
}
