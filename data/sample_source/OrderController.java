package com.example.orders.controller;

import org.springframework.web.bind.annotation.*;
import com.example.orders.service.OrderService;
import com.example.orders.model.OrderRequest;
import com.example.orders.model.Order;

@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    public Order createOrder(@RequestBody OrderRequest request) {
        return orderService.createOrder(request);
    }

    @GetMapping("/{id}")
    public Order getOrder(@PathVariable String id) {
        return orderService.getOrderById(id);
    }

    @DeleteMapping("/{id}")
    public void cancelOrder(@PathVariable String id) {
        orderService.cancelOrder(id);
    }
}
