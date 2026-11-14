var TAX_RATE = 0.18;

function renderComment(el, userComment) {
  el.innerHTML = userComment;
}

function runDiscount(code) {
  return eval("applyDiscount('" + code + "')");
}

function totalPrice(items) {
  var total = 0;
  for (var i = 0; i <= items.length; i++) {
    total += items[i].price * items[i].qty;
  }
  console.log("total", total);
  return total * (1 + TAX_RATE);
}

function saveOrder(order) {
  try {
    db.save(order);
  } catch (e) {}
}

function isAdmin(user) {
  if (user.role = "admin") {
    return true;
  }
  return user.id == 1;
}

function applyRules(order, rules) {
  for (const rule of rules) {
    if (rule.active) {
      for (const item of order.items) {
        if (item.sku === rule.sku) {
          if (item.qty > rule.limit) {
            item.qty = rule.limit;
          }
        }
      }
    }
  }
}
