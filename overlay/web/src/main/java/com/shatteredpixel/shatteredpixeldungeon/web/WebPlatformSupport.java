/*
 * Pixel Dungeon
 * Copyright (C) 2012-2015 Oleg Dolya
 *
 * Shattered Pixel Dungeon
 * Copyright (C) 2014-2026 Evan Debenham
 *
 * Web port modifications, 2026.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.g2d.PixmapPacker;
import com.badlogic.gdx.graphics.g2d.freetype.FreeTypeFontGenerator;
import com.watabou.utils.PlatformSupport;

import java.util.HashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WebPlatformSupport extends PlatformSupport {

    private static FreeTypeFontGenerator basicFontGenerator;
    private static FreeTypeFontGenerator asianFontGenerator;

    private static final Matcher ASIAN_MATCHER = Pattern.compile(
            "\\p{InHangul_Syllables}|" +
            "\\p{InCJK_Unified_Ideographs}|\\p{InCJK_Symbols_and_Punctuation}|\\p{InHalfwidth_and_Fullwidth_Forms}|" +
            "\\p{InHiragana}|\\p{InKatakana}"
    ).matcher("");

    private final Pattern regularSplitter = Pattern.compile(
            "(?<=\\n)|(?=\\n)|(?<=_)|(?=_)|(?<=\\*\\*)|(?=\\*\\*)|" +
            "(?<=\\p{InHiragana})|(?=\\p{InHiragana})|" +
            "(?<=\\p{InKatakana})|(?=\\p{InKatakana})|" +
            "(?<=\\p{InCJK_Unified_Ideographs})|(?=\\p{InCJK_Unified_Ideographs})|" +
            "(?<=\\p{InCJK_Symbols_and_Punctuation})|(?=\\p{InCJK_Symbols_and_Punctuation})"
    );

    private final Pattern regularSplitterMultiline = Pattern.compile(
            "(?<= )|(?= )|(?<=\\n)|(?=\\n)|(?<=_)|(?=_)|(?<=\\*\\*)|(?=\\*\\*)|" +
            "(?<=\\p{InHiragana})|(?=\\p{InHiragana})|" +
            "(?<=\\p{InKatakana})|(?=\\p{InKatakana})|" +
            "(?<=\\p{InCJK_Unified_Ideographs})|(?=\\p{InCJK_Unified_Ideographs})|" +
            "(?<=\\p{InCJK_Symbols_and_Punctuation})|(?=\\p{InCJK_Symbols_and_Punctuation})"
    );

    @Override
    public void updateDisplaySize() {
        // The browser canvas tracks the host viewport.
    }

    @Override
    public boolean supportsFullScreen() {
        // Browser fullscreen requires a user gesture. Keep the game's fullscreen
        // toggle disabled until a dedicated web UI flow is added.
        return false;
    }

    @Override
    public void updateSystemUI() {
        // No native system bars to control in the browser.
    }

    @Override
    public boolean connectedToUnmeteredNetwork() {
        return true;
    }

    @Override
    public boolean supportsVibration() {
        return false;
    }

    @Override
    public void setupFontGenerators(int pageSize, boolean systemFont) {
        if (fonts != null && this.pageSize == pageSize && this.systemfont == systemFont) {
            return;
        }

        this.pageSize = pageSize;
        this.systemfont = systemFont;

        resetGenerators(false);
        fonts = new HashMap<>();

        if (systemFont) {
            basicFontGenerator = asianFontGenerator =
                    new FreeTypeFontGenerator(Gdx.files.internal("fonts/droid_sans.ttf"));
        } else {
            basicFontGenerator =
                    new FreeTypeFontGenerator(Gdx.files.internal("fonts/pixel_font.ttf"));
            asianFontGenerator =
                    new FreeTypeFontGenerator(Gdx.files.internal("fonts/droid_sans.ttf"));
        }

        fonts.put(basicFontGenerator, new HashMap<>());
        fonts.put(asianFontGenerator, new HashMap<>());

        packer = new PixmapPacker(pageSize, pageSize, Pixmap.Format.RGBA8888, 1, false);
    }

    @Override
    protected FreeTypeFontGenerator getGeneratorForString(String input) {
        if (ASIAN_MATCHER.reset(input).find()) {
            return asianFontGenerator;
        }
        return basicFontGenerator;
    }

    @Override
    public String[] splitforTextBlock(String text, boolean multiline) {
        return (multiline ? regularSplitterMultiline : regularSplitter).split(text);
    }
}
