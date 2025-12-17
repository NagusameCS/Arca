package com.arcabank.screen;

import com.arcabank.ArcaBankClient;
import com.arcabank.api.ArcaApiClient;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.CyclingButtonWidget;
import net.minecraft.client.gui.widget.TextFieldWidget;
import net.minecraft.text.Text;

/**
 * Screen for reporting trades
 */
public class ReportTradeScreen extends Screen {
    private static final int FIELD_WIDTH = 180;
    private static final int LABEL_WIDTH = 100;

    private final Screen parent;

    // Form fields
    private TextFieldWidget itemNameField;
    private TextFieldWidget quantityField;
    private TextFieldWidget caratsField;
    private TextFieldWidget goldenCaratsField;
    private TextFieldWidget counterpartyField;

    // Trade type selector
    private CyclingButtonWidget<TradeType> tradeTypeButton;
    private CyclingButtonWidget<Category> categoryButton;

    private TradeType selectedTradeType = TradeType.SELL;
    private Category selectedCategory = Category.OTHER;

    private String statusText = "";
    private boolean isSubmitting = false;

    public ReportTradeScreen(Screen parent) {
        super(Text.translatable("arcabank.screen.report_trade"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        super.init();

        int centerX = this.width / 2;
        int startY = 45;
        int rowHeight = 25;
        int fieldX = centerX - FIELD_WIDTH / 2 + 30;
        int labelX = fieldX - LABEL_WIDTH;

        // Trade Type selector
        tradeTypeButton = CyclingButtonWidget.<TradeType>builder(type -> Text.literal(type.displayName))
                .values(TradeType.values())
                .initially(selectedTradeType)
                .build(fieldX, startY, FIELD_WIDTH, 20, Text.literal("Trade Type"), (button, value) -> {
                    selectedTradeType = value;
                });
        this.addDrawableChild(tradeTypeButton);

        // Item name
        itemNameField = new TextFieldWidget(this.textRenderer, fieldX, startY + rowHeight, FIELD_WIDTH, 18, Text.literal("Item"));
        itemNameField.setPlaceholder(Text.literal("Diamond Pickaxe"));
        itemNameField.setMaxLength(100);
        this.addSelectableChild(itemNameField);

        // Quantity
        quantityField = new TextFieldWidget(this.textRenderer, fieldX, startY + rowHeight * 2, FIELD_WIDTH, 18, Text.literal("Quantity"));
        quantityField.setPlaceholder(Text.literal("1"));
        quantityField.setText("1");
        quantityField.setMaxLength(10);
        this.addSelectableChild(quantityField);

        // Carats
        caratsField = new TextFieldWidget(this.textRenderer, fieldX, startY + rowHeight * 3, FIELD_WIDTH, 18, Text.literal("Carats"));
        caratsField.setPlaceholder(Text.literal("0.00"));
        caratsField.setText("0");
        caratsField.setMaxLength(15);
        this.addSelectableChild(caratsField);

        // Golden Carats
        goldenCaratsField = new TextFieldWidget(this.textRenderer, fieldX, startY + rowHeight * 4, FIELD_WIDTH, 18, Text.literal("Golden Carats"));
        goldenCaratsField.setPlaceholder(Text.literal("0.00"));
        goldenCaratsField.setText("0");
        goldenCaratsField.setMaxLength(15);
        this.addSelectableChild(goldenCaratsField);

        // Category selector
        categoryButton = CyclingButtonWidget.<Category>builder(cat -> Text.literal(cat.displayName))
                .values(Category.values())
                .initially(selectedCategory)
                .build(fieldX, startY + rowHeight * 5, FIELD_WIDTH, 20, Text.literal("Category"), (button, value) -> {
                    selectedCategory = value;
                });
        this.addDrawableChild(categoryButton);

        // Counterparty (optional)
        counterpartyField = new TextFieldWidget(this.textRenderer, fieldX, startY + rowHeight * 6, FIELD_WIDTH, 18, Text.literal("Counterparty"));
        counterpartyField.setPlaceholder(Text.literal("(Optional) Player name"));
        counterpartyField.setMaxLength(50);
        this.addSelectableChild(counterpartyField);

        // Submit button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.submit"),
                button -> submitTrade()
        ).dimensions(centerX - 105, startY + rowHeight * 7 + 10, 100, 20).build());

        // Cancel button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.cancel"),
                button -> this.close()
        ).dimensions(centerX + 5, startY + rowHeight * 7 + 10, 100, 20).build());

        this.setInitialFocus(itemNameField);
    }

    private void submitTrade() {
        if (isSubmitting) return;

        // Validate fields
        String itemName = itemNameField.getText().trim();
        if (itemName.isEmpty()) {
            statusText = "§cItem name is required";
            return;
        }

        int quantity;
        try {
            quantity = Integer.parseInt(quantityField.getText().trim());
            if (quantity <= 0) throw new NumberFormatException();
        } catch (NumberFormatException e) {
            statusText = "§cInvalid quantity";
            return;
        }

        double carats;
        try {
            carats = Double.parseDouble(caratsField.getText().trim());
        } catch (NumberFormatException e) {
            statusText = "§cInvalid carat amount";
            return;
        }

        double goldenCarats;
        try {
            goldenCarats = Double.parseDouble(goldenCaratsField.getText().trim());
        } catch (NumberFormatException e) {
            statusText = "§cInvalid golden carat amount";
            return;
        }

        if (carats <= 0 && goldenCarats <= 0) {
            statusText = "§cTrade must involve currency";
            return;
        }

        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) {
            statusText = "§cNo player found";
            return;
        }

        String uuid = client.player.getUuidAsString();
        String counterparty = counterpartyField.getText().trim();

        // Build request
        ArcaApiClient.TradeReportRequest request = new ArcaApiClient.TradeReportRequest(
                uuid,
                selectedTradeType.apiValue,
                itemName,
                quantity,
                carats,
                goldenCarats
        ).withCategory(selectedCategory.apiValue);

        if (!counterparty.isEmpty()) {
            request.withCounterparty(counterparty);
        }

        // Add location
        if (client.world != null) {
            request.withLocation(
                    client.world.getRegistryKey().getValue().toString(),
                    (int) client.player.getX(),
                    (int) client.player.getY(),
                    (int) client.player.getZ()
            );
        }

        isSubmitting = true;
        statusText = "§7Submitting...";

        ArcaBankClient.getApiClient().reportTrade(request).thenAccept(response -> {
            isSubmitting = false;
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();
                statusText = String.format("§aTrade #%d reported! Price: %.4f/item",
                        data.trade_id, data.price_per_item);

                // Clear form for next entry
                itemNameField.setText("");
                quantityField.setText("1");
                caratsField.setText("0");
                goldenCaratsField.setText("0");
                counterpartyField.setText("");
            } else {
                statusText = "§c" + (response.getError() != null ? response.getError() : "Failed to report trade");
            }
        });
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        this.renderBackground(context, mouseX, mouseY, delta);

        // Title
        context.drawCenteredTextWithShadow(this.textRenderer, this.title, this.width / 2, 15, 0xFFFFFF);

        int startY = 45;
        int rowHeight = 25;
        int labelX = this.width / 2 - FIELD_WIDTH / 2 - 70;

        // Labels
        context.drawTextWithShadow(this.textRenderer, Text.literal("Trade Type:"), labelX, startY + 6, 0xAAAAAA);
        context.drawTextWithShadow(this.textRenderer, Text.literal("Item:"), labelX, startY + rowHeight + 4, 0xAAAAAA);
        context.drawTextWithShadow(this.textRenderer, Text.literal("Quantity:"), labelX, startY + rowHeight * 2 + 4, 0xAAAAAA);
        context.drawTextWithShadow(this.textRenderer, Text.literal("Carats:"), labelX, startY + rowHeight * 3 + 4, 0xAAAAAA);
        context.drawTextWithShadow(this.textRenderer, Text.literal("Golden Carats:"), labelX, startY + rowHeight * 4 + 4, 0xAAAAAA);
        context.drawTextWithShadow(this.textRenderer, Text.literal("Category:"), labelX, startY + rowHeight * 5 + 6, 0xAAAAAA);
        context.drawTextWithShadow(this.textRenderer, Text.literal("Traded With:"), labelX, startY + rowHeight * 6 + 4, 0xAAAAAA);

        // Render text fields
        itemNameField.render(context, mouseX, mouseY, delta);
        quantityField.render(context, mouseX, mouseY, delta);
        caratsField.render(context, mouseX, mouseY, delta);
        goldenCaratsField.render(context, mouseX, mouseY, delta);
        counterpartyField.render(context, mouseX, mouseY, delta);

        // Status text
        if (!statusText.isEmpty()) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal(statusText),
                    this.width / 2, startY + rowHeight * 8 + 15, 0xFFFFFF);
        }

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

    // Trade type enum
    private enum TradeType {
        BUY("BUY", "Buy"),
        SELL("SELL", "Sell"),
        EXCHANGE("EXCHANGE", "Exchange");

        final String apiValue;
        final String displayName;

        TradeType(String apiValue, String displayName) {
            this.apiValue = apiValue;
            this.displayName = displayName;
        }
    }

    // Category enum
    private enum Category {
        DIAMOND("DIAMOND", "Diamond"),
        NETHERITE("NETHERITE", "Netherite"),
        ENCHANTED_GEAR("ENCHANTED_GEAR", "Enchanted Gear"),
        BUILDING_MATERIALS("BUILDING_MATERIALS", "Building Materials"),
        FOOD("FOOD", "Food"),
        POTIONS("POTIONS", "Potions"),
        REDSTONE("REDSTONE", "Redstone"),
        RARE_ITEMS("RARE_ITEMS", "Rare Items"),
        SERVICES("SERVICES", "Services"),
        OTHER("OTHER", "Other");

        final String apiValue;
        final String displayName;

        Category(String apiValue, String displayName) {
            this.apiValue = apiValue;
            this.displayName = displayName;
        }
    }
}
