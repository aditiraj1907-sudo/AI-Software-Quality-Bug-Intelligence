async function syncCart(userIds) {
  for (const id of userIds) {
    const cart = await fetchCart(id);
    render(cart);
  }
}

function loadPrices() {
  fetch("/api/prices").then(r => r.json()).then(p => render(p));
}

function parseQty(input) {
  return parseInt(input.trim());
}

// TODO: debounce quantity updates
