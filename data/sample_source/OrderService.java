package com.example.orders.service;

import org.springframework.stereotype.Service;
import com.example.orders.model.OrderRequest;
import com.example.orders.model.Order;

@Service
public class OrderService {

    public Order createOrder(OrderRequest request) {
        double total = 0;
        for (var item : request.getItems()) {
            total += item.getPrice() * item.getQuantity();
        }

        double discount = 0;
        // Business Rule: Gold customers get 10% off on orders over 500
        if ("GOLD".equals(request.getCustomerTier()) && total > 500) {
            discount = total * 0.10;
        }

        Order order = new Order();
        order.setCustomerId(request.getCustomerId());
        order.setTotalAmount(total - discount);
        order.setDiscountApplied(discount);
        order.setStatus("PENDING");
        
        return order;
    }

    public void cancelOrder(String id) {
        Order order = getOrderById(id);
        if (!"PENDING".equals(order.getStatus())) {
            throw new IllegalStateException("Only PENDING orders can be cancelled");
        }
        order.setStatus("CANCELLED");
    }
    
    public Order getOrderById(String id) {
        // Mock implementation
        Order order = new Order();
        order.setId(id);
        order.setStatus("PENDING");
        return order;
    }
}
