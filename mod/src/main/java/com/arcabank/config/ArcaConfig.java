package com.arcabank.config;

import com.arcabank.ArcaBankClient;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Configuration for Arca Bank mod
 */
public class ArcaConfig {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String CONFIG_FILE = "arcabank.json";

    // Configuration fields
    private String apiUrl = "http://localhost:8080";
    private int requestTimeoutMs = 5000;
    private boolean showNotifications = true;
    private boolean autoReportTrades = false;
    private String defaultCategory = "OTHER";

    // Getters
    public String getApiUrl() {
        return apiUrl;
    }

    public int getRequestTimeoutMs() {
        return requestTimeoutMs;
    }

    public boolean isShowNotifications() {
        return showNotifications;
    }

    public boolean isAutoReportTrades() {
        return autoReportTrades;
    }

    public String getDefaultCategory() {
        return defaultCategory;
    }

    // Setters
    public void setApiUrl(String apiUrl) {
        this.apiUrl = apiUrl;
    }

    public void setRequestTimeoutMs(int requestTimeoutMs) {
        this.requestTimeoutMs = requestTimeoutMs;
    }

    public void setShowNotifications(boolean showNotifications) {
        this.showNotifications = showNotifications;
    }

    public void setAutoReportTrades(boolean autoReportTrades) {
        this.autoReportTrades = autoReportTrades;
    }

    public void setDefaultCategory(String defaultCategory) {
        this.defaultCategory = defaultCategory;
    }

    /**
     * Load configuration from file or create default
     */
    public static ArcaConfig load() {
        Path configPath = getConfigPath();

        if (Files.exists(configPath)) {
            try {
                String json = Files.readString(configPath);
                ArcaConfig config = GSON.fromJson(json, ArcaConfig.class);
                if (config != null) {
                    return config;
                }
            } catch (IOException e) {
                ArcaBankClient.LOGGER.error("Failed to load config, using defaults", e);
            }
        }

        // Create and save default config
        ArcaConfig config = new ArcaConfig();
        config.save();
        return config;
    }

    /**
     * Save configuration to file
     */
    public void save() {
        Path configPath = getConfigPath();

        try {
            Files.createDirectories(configPath.getParent());
            Files.writeString(configPath, GSON.toJson(this));
        } catch (IOException e) {
            ArcaBankClient.LOGGER.error("Failed to save config", e);
        }
    }

    private static Path getConfigPath() {
        return FabricLoader.getInstance()
                .getConfigDir()
                .resolve(CONFIG_FILE);
    }
}
