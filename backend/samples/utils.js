function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function isEmpty(list) {
  return list == null || list.length === 0;
}

function formatINR(n) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(n);
}
