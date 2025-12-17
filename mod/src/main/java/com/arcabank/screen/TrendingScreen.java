package com.arcabank.screen;

import com.arcabank.ArcaBankClient;
import com.arcabank.api.ArcaApiClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

import java.util.ArrayList;
import java.util.List;

/**
 * Screen showing trending items by trading volume
 */
public class TrendingScreen extends Screen {
    private final Screen parent;
    private List<TrendingItem> items = new ArrayList<>();
    private boolean isLoading = true;
    private String errorMessage = null;

    public TrendingScreen(Screen parent) {
        super(Text.translatable("arcabank.button.trending"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        super.init();

        // Back button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.back"),
                button -> this.close()
        ).dimensions(this.width / 2 - 50, this.height - 40, 100, 20).build());

        // Refresh button
        this.addDrawableChild(ButtonWidget.builder(
                Text.literal("Refresh"),
                button -> loadTrending()
        ).dimensions(this.width / 2 + 60, this.height - 40, 60, 20).build());

        loadTrending();
    }

    private void loadTrending() {
        isLoading = true;
        errorMessage = null;
        items.clear();

        ArcaBankClient.getApiClient().getTrendingItems(15).thenAccept(response -> {
            isLoading = false;
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();
                if (data.items != null) {
                    for (var item : data.items) {
                        items.add(new TrendingItem(
                                item.item_name,
                                item.category,
                                item.current_price,
                                item.trade_count_24h,
                                item.volume_24h
                        ));
                    }
                }
                if (items.isEmpty()) {
                    errorMessage = "No trending items yet";
                }
            } else {
                errorMessage = response.getError() != null ? response.getError() : "Failed to load trending items";
            }
        });
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        this.renderBackground(context, mouseX, mouseY, delta);

        // Title
        context.drawCenteredTextWithShadow(this.textRenderer, this.title, this.width / 2, 15, 0xFFFFFF);
        context.drawCenteredTextWithShadow(this.textRenderer,
                Text.literal("§7Most traded items in the last 24 hours"),
                this.width / 2, 28, 0xFFFFFF);

        if (isLoading) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal("§7Loading..."), this.width / 2, this.height / 2, 0xFFFFFF);
        } else if (errorMessage != null) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal("§e" + errorMessage), this.width / 2, this.height / 2, 0xFFFFFF);
        } else {
            // Header
            int headerY = 45;
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7#"), 20, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Item"), 40, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Category"), 160, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Price"), 250, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Volume"), 310, headerY, 0xFFFFFF);

            // Items
            int y = 60;
            int rank = 1;
            for (TrendingItem item : items) {
                // Rank with medal colors
                String rankColor;
                if (rank == 1) rankColor = "§6"; // Gold
                else if (rank == 2) rankColor = "§7"; // Silver
                else if (rank == 3) rankColor = "§c"; // Bronze
                else rankColor = "§f";

                context.drawTextWithShadow(this.textRenderer, Text.literal(rankColor + rank), 20, y, 0xFFFFFF);

                // Item name (truncate if needed)
                String itemName = item.name;
                if (itemName.length() > 15) {
                    itemName = itemName.substring(0, 12) + "...";
                }
                context.drawTextWithShadow(this.textRenderer, Text.literal("§f" + itemName), 40, y, 0xFFFFFF);

                // Category
                String catDisplay = formatCategory(item.category);
                context.drawTextWithShadow(this.textRenderer, Text.literal("§7" + catDisplay), 160, y, 0xFFFFFF);

                // Price
                context.drawTextWithShadow(this.textRenderer,
                        Text.literal(String.format("§f%.2f", item.price)), 250, y, 0xFFFFFF);

                // Volume
                String volumeStr;
                if (item.volume >= 1000) {
                    volumeStr = String.format("%.1fK", item.volume / 1000);
                } else {
                    volumeStr = String.format("%.0f", item.volume);
                }
                context.drawTextWithShadow(this.textRenderer,
                        Text.literal("§a" + volumeStr + " §7(" + item.tradeCount + ")"), 310, y, 0xFFFFFF);

                y += 16;
                rank++;
            }
        }

        super.render(context, mouseX, mouseY, delta);
    }

    private String formatCategory(String category) {
        if (category == null) return "Other";
        switch (category) {
            case "DIAMOND": return "Diamond";
            case "NETHERITE": return "Netherite";
            case "ENCHANTED_GEAR": return "Enchanted";
            case "BUILDING_MATERIALS": return "Building";
            case "FOOD": return "Food";
            case "POTIONS": return "Potions";
            case "REDSTONE": return "Redstone";
            case "RARE_ITEMS": return "Rare";
            case "SERVICES": return "Services";
            default: return "Other";
        }
    }

    @Override
    public void close() {
        if (parent != null) {
            this.client.setScreen(parent);
        } else {
            super.close();
        }
    }

    @Override
    public boolean shouldPause() {
        return false;
    }

    private static class TrendingItem {
        final String name;
        final String category;
        final double price;
        final int tradeCount;
        final double volume;

        TrendingItem(String name, String category, double price, int tradeCount, double volume) {
            this.name = name;
            this.category = category;
            this.price = price;
            this.tradeCount = tradeCount;
            this.volume = volume;
        }
    }
}
