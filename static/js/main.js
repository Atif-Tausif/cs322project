/**
 * Main JavaScript file
 * Handles general site functionality
 */

$(document).ready(function() {
    // Update cart count
    updateCartCount();
    
    // Handle cart operations
    $(document).on('click', '.add-to-cart', function(e) {
        e.preventDefault();
        const dishId = $(this).data('dish-id');
        
        // Try to get quantity from nearby input field first
        let quantity = 1;
        const quantityInput = $(this).closest('.card, .container, .row').find('#quantity, input[type="number"][id*="quantity"], .quantity-input');
        if (quantityInput.length > 0) {
            const inputVal = parseInt(quantityInput.val());
            if (!isNaN(inputVal) && inputVal > 0) {
                quantity = inputVal;
            }
        } else {
            // Fallback to data attribute
            quantity = parseInt($(this).data('quantity') || 1);
        }
        
        addToCart(dishId, quantity);
    });
    
    // Handle remove from cart
    $('.remove-from-cart').on('click', function(e) {
        e.preventDefault();
        const dishId = $(this).data('dish-id');
        removeFromCart(dishId);
    });
    
    // Handle quantity updates
    $(document).on('change', '.cart-quantity', function() {
        const dishId = $(this).data('dish-id');
        let quantity = parseInt($(this).val());
        
        // Validate quantity
        if (isNaN(quantity) || quantity < 1) {
            quantity = 1;
            $(this).val(1);
        }
        if (quantity > 999) {
            quantity = 999;
            $(this).val(999);
        }
        
        updateCartQuantity(dishId, quantity);
    });
});

/**
 * Update cart count in navbar
 */
function updateCartCount() {
    const cart = getCartFromSession();
    $('#cart-count').text(cart.length);
}

/**
 * Get cart from session (fallback to empty array)
 */
function getCartFromSession() {
    // This is a client-side helper
    // Actual cart is stored in Flask session
    return [];
}

/**
 * Add item to cart
 */
function addToCart(dishId, quantity = 1) {
    $.ajax({
        url: '/api/v1/cart/add',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            dish_id: dishId,
            quantity: quantity
        }),
        success: function(response) {
            if (response.success) {
                $('#cart-count').text(response.cart_count);
                showNotification('Added to cart!', 'success');
            } else {
                showNotification(response.message || 'Failed to add to cart', 'danger');
            }
        },
        error: function() {
            showNotification('Error adding to cart', 'danger');
        }
    });
}

/**
 * Remove item from cart
 */
function removeFromCart(dishId) {
    $.ajax({
        url: '/api/v1/cart/remove',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            dish_id: dishId
        }),
        success: function(response) {
            if (response.success) {
                $('#cart-count').text(response.cart_count);
                location.reload(); // Reload to update cart display
            } else {
                showNotification(response.message || 'Failed to remove from cart', 'danger');
            }
        },
        error: function() {
            showNotification('Error removing from cart', 'danger');
        }
    });
}

/**
 * Update cart item quantity
 */
function updateCartQuantity(dishId, quantity) {
    // Validate quantity before sending
    if (!dishId || !quantity || quantity < 1 || quantity > 999) {
        showNotification('Invalid quantity. Please enter a number between 1 and 999.', 'danger');
        return;
    }
    
    $.ajax({
        url: '/api/v1/cart/update',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            dish_id: dishId,
            quantity: quantity
        }),
        success: function(response) {
            if (response.success) {
                $('#cart-count').text(response.cart_count);
                location.reload(); // Reload to update totals
            } else {
                showNotification(response.message || 'Failed to update cart', 'danger');
                // Reload to restore correct state
                location.reload();
            }
        },
        error: function() {
            showNotification('Error updating cart', 'danger');
            // Reload to restore correct state
            location.reload();
        }
    });
}

/**
 * Show notification/toast
 */
function showNotification(message, type = 'info') {
    // Create toast notification
    const toast = $(`
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `);
    
    $('body').append(toast);
    const bsToast = new bootstrap.Toast(toast[0]);
    bsToast.show();
    
    // Remove after hide
    toast.on('hidden.bs.toast', function() {
        $(this).remove();
    });
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return '$' + parseFloat(amount).toFixed(2);
}

/**
 * Place order
 * Note: This is a fallback implementation. Cart page should override this.
 */
function placeOrder() {
    // If we're on the cart page, try to read from DOM first
    if ($('.cart-quantity').length > 0) {
        const items = [];
        $('.cart-quantity').each(function() {
            const dishId = $(this).data('dish-id');
            const quantity = parseInt($(this).val()) || 1;
            
            if (dishId && quantity > 0) {
                items.push({
                    dish_id: dishId,
                    quantity: quantity
                });
            }
        });
        
        if (items.length === 0) {
            showNotification('Your cart is empty', 'warning');
            return;
        }
        
        $.ajax({
            url: '/api/v1/order',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ items: items }),
            success: function(response) {
                if (response.success) {
                    showNotification('Order placed successfully!', 'success');
                    setTimeout(function() {
                        window.location.href = '/orders';
                    }, 1500);
                } else {
                    showNotification(response.message || 'Failed to place order', 'danger');
                }
            },
            error: function() {
                showNotification('Error placing order', 'danger');
            }
        });
        return;
    }
    
    // Fallback for other pages (shouldn't normally be called)
    const cart = getCartItems();
    
    if (cart.length === 0) {
        showNotification('Your cart is empty', 'warning');
        return;
    }
    
    const items = cart.map(item => ({
        dish_id: item.dish_id,
        quantity: item.quantity
    }));
    
    $.ajax({
        url: '/api/v1/order',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            items: items
        }),
        success: function(response) {
            if (response.success) {
                showNotification('Order placed successfully!', 'success');
                setTimeout(function() {
                    window.location.href = '/orders';
                }, 1500);
            } else {
                showNotification(response.message || 'Failed to place order', 'danger');
            }
        },
        error: function() {
            showNotification('Error placing order', 'danger');
        }
    });
}

/**
 * Get cart items (helper - actual data comes from server)
 */
function getCartItems() {
    // This would typically be populated from the page
    return [];
}
