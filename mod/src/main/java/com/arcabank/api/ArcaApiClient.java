package com.arcabank.api;

import com.arcabank.ArcaBankClient;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

/**
 * HTTP client for communicating with Arca Bank REST API
 */
public class ArcaApiClient {
    private static final Gson GSON = new Gson();

    private final String baseUrl;
    private final HttpClient httpClient;

    public ArcaApiClient(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(ArcaBankClient.getConfig().getRequestTimeoutMs()))
                .build();
    }

    // ==================== BALANCE & MARKET ====================

    /**
     * Get player balance by Minecraft UUID
     */
    public CompletableFuture<ApiResponse<BalanceResponse>> getBalance(String uuid) {
        return get("/api/balance/" + uuid, BalanceResponse.class);
    }

    /**
     * Get current market status
     */
    public CompletableFuture<ApiResponse<MarketResponse>> getMarket() {
        return get("/api/market", MarketResponse.class);
    }

    /**
     * Get treasury information
     */
    public CompletableFuture<ApiResponse<TreasuryResponse>> getTreasury() {
        return get("/api/treasury", TreasuryResponse.class);
    }

    /**
     * Check player permissions
     */
    public CompletableFuture<ApiResponse<PermissionsResponse>> checkPermissions(String uuid) {
        return get("/api/is_banker/" + uuid, PermissionsResponse.class);
    }

    // ==================== TRADE OPERATIONS ====================

    /**
     * Report a trade
     */
    public CompletableFuture<ApiResponse<TradeReportResponse>> reportTrade(TradeReportRequest request) {
        return post("/api/trade/report", request, TradeReportResponse.class);
    }

    /**
     * Get item price
     */
    public CompletableFuture<ApiResponse<ItemPriceResponse>> getItemPrice(String itemName) {
        return get("/api/trade/price/" + encodeUrl(itemName), ItemPriceResponse.class);
    }

    /**
     * Get trending items
     */
    public CompletableFuture<ApiResponse<TrendingItemsResponse>> getTrendingItems(int limit) {
        return get("/api/trade/trending?limit=" + limit, TrendingItemsResponse.class);
    }

    /**
     * Get player's trade history
     */
    public CompletableFuture<ApiResponse<TradeHistoryResponse>> getTradeHistory(String uuid, int limit) {
        return get("/api/trade/history/" + uuid + "?limit=" + limit, TradeHistoryResponse.class);
    }

    /**
     * Get player's trading stats
     */
    public CompletableFuture<ApiResponse<TradeStatsResponse>> getTradeStats(String uuid) {
        return get("/api/trade/stats/" + uuid, TradeStatsResponse.class);
    }

    // ==================== HTTP HELPERS ====================

    private <T> CompletableFuture<ApiResponse<T>> get(String path, Class<T> responseClass) {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .header("Content-Type", "application/json")
                .GET()
                .timeout(Duration.ofMillis(ArcaBankClient.getConfig().getRequestTimeoutMs()))
                .build();

        return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(response -> parseResponse(response, responseClass))
                .exceptionally(e -> {
                    ArcaBankClient.LOGGER.error("API request failed: {}", path, e);
                    return ApiResponse.error("Connection failed: " + e.getMessage());
                });
    }

    private <T, R> CompletableFuture<ApiResponse<R>> post(String path, T body, Class<R> responseClass) {
        String json = GSON.toJson(body);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .timeout(Duration.ofMillis(ArcaBankClient.getConfig().getRequestTimeoutMs()))
                .build();

        return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(response -> parseResponse(response, responseClass))
                .exceptionally(e -> {
                    ArcaBankClient.LOGGER.error("API POST failed: {}", path, e);
                    return ApiResponse.error("Connection failed: " + e.getMessage());
                });
    }

    private <T> ApiResponse<T> parseResponse(HttpResponse<String> response, Class<T> responseClass) {
        try {
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                T data = GSON.fromJson(response.body(), responseClass);
                return ApiResponse.success(data);
            } else {
                // Try to parse error message
                JsonObject json = JsonParser.parseString(response.body()).getAsJsonObject();
                String error = json.has("detail") ? json.get("detail").getAsString() :
                               json.has("error") ? json.get("error").getAsString() :
                               "Request failed";
                return ApiResponse.error(error);
            }
        } catch (Exception e) {
            ArcaBankClient.LOGGER.error("Failed to parse response", e);
            return ApiResponse.error("Failed to parse response");
        }
    }

    private String encodeUrl(String value) {
        try {
            return java.net.URLEncoder.encode(value, "UTF-8");
        } catch (Exception e) {
            return value;
        }
    }

    // ==================== RESPONSE CLASSES ====================

    public static class ApiResponse<T> {
        private final boolean success;
        private final T data;
        private final String error;

        private ApiResponse(boolean success, T data, String error) {
            this.success = success;
            this.data = data;
            this.error = error;
        }

        public static <T> ApiResponse<T> success(T data) {
            return new ApiResponse<>(true, data, null);
        }

        public static <T> ApiResponse<T> error(String error) {
            return new ApiResponse<>(false, null, error);
        }

        public boolean isSuccess() {
            return success;
        }

        public T getData() {
            return data;
        }

        public String getError() {
            return error;
        }
    }

    // Response DTOs
    public static class BalanceResponse {
        public boolean success;
        public String minecraft_uuid;
        public String minecraft_username;
        public double carats;
        public double golden_carats;
        public double total_in_carats;
    }

    public static class MarketResponse {
        public boolean success;
        public double carat_price;
        public double index;
        public String status;
        public boolean is_frozen;
        public double change_24h;
    }

    public static class TreasuryResponse {
        public boolean success;
        public double total_diamonds;
        public double total_carats;
        public double total_golden_carats;
        public double book_value;
        public double reserve_ratio;
    }

    public static class PermissionsResponse {
        public boolean success;
        public boolean is_banker;
        public boolean is_head_banker;
        public boolean is_consumer;
        public boolean can_trade;
        public String role;
    }

    public static class TradeReportResponse {
        public boolean success;
        public int trade_id;
        public String trade_type;
        public String item_name;
        public double price_per_item;
        public String message;
    }

    public static class ItemPriceResponse {
        public boolean success;
        public boolean found;
        public String item_name;
        public String category;
        public double current_price;
        public int trade_count_24h;
        public double volume_24h;
    }

    public static class TrendingItemsResponse {
        public boolean success;
        public TrendingItem[] items;

        public static class TrendingItem {
            public String item_name;
            public String category;
            public double current_price;
            public int trade_count_24h;
            public double volume_24h;
        }
    }

    public static class TradeHistoryResponse {
        public boolean success;
        public int trade_count;
        public TradeEntry[] trades;

        public static class TradeEntry {
            public int id;
            public String type;
            public String item;
            public int quantity;
            public double carats;
            public double golden_carats;
            public double price_per_item;
            public String counterparty;
            public boolean verified;
            public String timestamp;
        }
    }

    public static class TradeStatsResponse {
        public boolean success;
        public boolean has_stats;
        public int total_trades;
        public int buy_count;
        public int sell_count;
        public double total_volume;
        public double average_trade_size;
        public int verified_trades;
        public double reputation;
    }

    // Request DTOs
    public static class TradeReportRequest {
        public String minecraft_uuid;
        public String trade_type;
        public String item_name;
        public int item_quantity;
        public double carat_amount;
        public double golden_carat_amount;
        public String item_category;
        public String counterparty_name;
        public String world_name;
        public Integer location_x;
        public Integer location_y;
        public Integer location_z;
        public String notes;

        public TradeReportRequest(String uuid, String tradeType, String itemName,
                                   int quantity, double carats, double goldenCarats) {
            this.minecraft_uuid = uuid;
            this.trade_type = tradeType;
            this.item_name = itemName;
            this.item_quantity = quantity;
            this.carat_amount = carats;
            this.golden_carat_amount = goldenCarats;
            this.item_category = "OTHER";
        }

        public TradeReportRequest withCategory(String category) {
            this.item_category = category;
            return this;
        }

        public TradeReportRequest withCounterparty(String name) {
            this.counterparty_name = name;
            return this;
        }

        public TradeReportRequest withLocation(String world, int x, int y, int z) {
            this.world_name = world;
            this.location_x = x;
            this.location_y = y;
            this.location_z = z;
            return this;
        }

        public TradeReportRequest withNotes(String notes) {
            this.notes = notes;
            return this;
        }
    }
}
