package com.arcabank.screen;

import com.arcabank.ArcaBankClient;
import com.arcabank.api.ArcaApiClient;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

import java.util.ArrayList;
import java.util.List;

/**
 * Screen showing player's trade history
 */
public class MyTradesScreen extends Screen {
    private static final int TRADES_PER_PAGE = 8;

    private final Screen parent;
    private List<TradeEntry> trades = new ArrayList<>();
    private int currentPage = 0;
    private int totalTrades = 0;
    private boolean isLoading = true;
    private String errorMessage = null;

    private ButtonWidget prevButton;
    private ButtonWidget nextButton;

    public MyTradesScreen(Screen parent) {
        super(Text.translatable("arcabank.screen.my_trades"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        super.init();

        int buttonY = this.height - 40;

        // Previous page
        prevButton = this.addDrawableChild(ButtonWidget.builder(
                Text.literal("< Prev"),
                button -> {
                    if (currentPage > 0) {
                        currentPage--;
                    }
                }
        ).dimensions(this.width / 2 - 120, buttonY, 70, 20).build());

        // Back button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.back"),
                button -> this.close()
        ).dimensions(this.width / 2 - 35, buttonY, 70, 20).build());

        // Next page
        nextButton = this.addDrawableChild(ButtonWidget.builder(
                Text.literal("Next >"),
                button -> {
                    int maxPage = (trades.size() - 1) / TRADES_PER_PAGE;
                    if (currentPage < maxPage) {
                        currentPage++;
                    }
                }
        ).dimensions(this.width / 2 + 50, buttonY, 70, 20).build());

        loadTrades();
    }

    private void loadTrades() {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) {
            errorMessage = "No player found";
            isLoading = false;
            return;
        }

        String uuid = client.player.getUuidAsString();

        ArcaBankClient.getApiClient().getTradeHistory(uuid, 50).thenAccept(response -> {
            isLoading = false;
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();
                totalTrades = data.trade_count;
                trades.clear();

                if (data.trades != null) {
                    for (var trade : data.trades) {
                        trades.add(new TradeEntry(
                                trade.id,
                                trade.type,
                                trade.item,
                                trade.quantity,
                                trade.carats,
                                trade.golden_carats,
                                trade.counterparty,
                                trade.verified,
                                trade.timestamp
                        ));
                    }
                }
            } else {
                errorMessage = response.getError() != null ? response.getError() : "Failed to load trades";
            }
        });
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        this.renderBackground(context, mouseX, mouseY, delta);

        // Title
        context.drawCenteredTextWithShadow(this.textRenderer, this.title, this.width / 2, 15, 0xFFFFFF);

        if (isLoading) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal("§7Loading..."), this.width / 2, this.height / 2, 0xFFFFFF);
        } else if (errorMessage != null) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal("§c" + errorMessage), this.width / 2, this.height / 2, 0xFFFFFF);
        } else if (trades.isEmpty()) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal("§eNo trades found"), this.width / 2, this.height / 2, 0xFFFFFF);
        } else {
            // Header
            int headerY = 35;
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Type"), 20, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Item"), 70, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Qty"), 180, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Amount"), 220, headerY, 0xFFFFFF);
            context.drawTextWithShadow(this.textRenderer, Text.literal("§7Status"), 300, headerY, 0xFFFFFF);

            // Trades
            int startIndex = currentPage * TRADES_PER_PAGE;
            int endIndex = Math.min(startIndex + TRADES_PER_PAGE, trades.size());
            int y = 50;

            for (int i = startIndex; i < endIndex; i++) {
                TradeEntry trade = trades.get(i);

                String typeColor = trade.type.equals("BUY") ? "§a" : trade.type.equals("SELL") ? "§c" : "§e";
                context.drawTextWithShadow(this.textRenderer, Text.literal(typeColor + trade.type), 20, y, 0xFFFFFF);

                // Truncate item name if too long
                String itemName = trade.item;
                if (itemName.length() > 15) {
                    itemName = itemName.substring(0, 12) + "...";
                }
                context.drawTextWithShadow(this.textRenderer, Text.literal("§f" + itemName), 70, y, 0xFFFFFF);
                context.drawTextWithShadow(this.textRenderer, Text.literal("§f" + trade.quantity), 180, y, 0xFFFFFF);

                String amount;
                if (trade.goldenCarats > 0) {
                    amount = String.format("%.1fGC", trade.goldenCarats);
                } else {
                    amount = String.format("%.1fC", trade.carats);
                }
                context.drawTextWithShadow(this.textRenderer, Text.literal("§f" + amount), 220, y, 0xFFFFFF);

                String status = trade.verified ? "§a✓" : "§7○";
                context.drawTextWithShadow(this.textRenderer, Text.literal(status), 300, y, 0xFFFFFF);

                y += 18;
            }

            // Page info
            int totalPages = (trades.size() + TRADES_PER_PAGE - 1) / TRADES_PER_PAGE;
            String pageInfo = String.format("Page %d / %d (%d trades)", currentPage + 1, totalPages, totalTrades);
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal("§7" + pageInfo), this.width / 2, this.height - 55, 0xFFFFFF);
        }

        // Update button states
        prevButton.active = currentPage > 0;
        int maxPage = trades.isEmpty() ? 0 : (trades.size() - 1) / TRADES_PER_PAGE;
        nextButton.active = currentPage < maxPage;

        super.render(context, mouseX, mouseY, delta);
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

    private static class TradeEntry {
        final int id;
        final String type;
        final String item;
        final int quantity;
        final double carats;
        final double goldenCarats;
        final String counterparty;
        final boolean verified;
        final String timestamp;

        TradeEntry(int id, String type, String item, int quantity, double carats,
                   double goldenCarats, String counterparty, boolean verified, String timestamp) {
            this.id = id;
            this.type = type;
            this.item = item;
            this.quantity = quantity;
            this.carats = carats;
            this.goldenCarats = goldenCarats;
            this.counterparty = counterparty;
            this.verified = verified;
            this.timestamp = timestamp;
        }
    }
}
