package forge.tnk;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Turns a Forge-format mana cost string (e.g. "2 G G", "W", "no cost") into a concrete
 * list of basic land names that pay for it -- enough to data-drive casting tests without
 * hand-listing lands per card.
 *
 * Only handles plain generic-number + single-color-letter tokens (everything TNK's
 * commons currently use). Hybrid ("W/U"), Phyrexian ("W/P"), X, and snow (S) costs
 * return null so callers can skip those cards rather than mis-costing them.
 */
public final class ManaCostUtil {
    private static final Pattern INTEGER = Pattern.compile("\\d+");

    private ManaCostUtil() {
    }

    private static String basicLandFor(char color) {
        switch (color) {
            case 'W': return "Plains";
            case 'U': return "Island";
            case 'B': return "Swamp";
            case 'R': return "Mountain";
            case 'G': return "Forest";
            default: return null;
        }
    }

    /** @return a list of basic land names that pays this cost, or null if the cost uses a
     *          shape this util doesn't understand (hybrid, X, snow, ...). */
    public static List<String> landsFor(String forgeManaCost) {
        if (forgeManaCost == null || forgeManaCost.equals("no cost")) {
            return new ArrayList<>();
        }
        List<String> colorLands = new ArrayList<>();
        int generic = 0;

        for (String token : forgeManaCost.trim().split("\\s+")) {
            if (token.isEmpty()) {
                continue;
            }
            if (INTEGER.matcher(token).matches()) {
                generic += Integer.parseInt(token);
            } else if (token.length() == 1 && basicLandFor(token.charAt(0)) != null) {
                colorLands.add(basicLandFor(token.charAt(0)));
            } else {
                return null; // hybrid ("W/U"), Phyrexian ("W/P"), X, S (snow), C, etc.
            }
        }

        String genericFiller = colorLands.isEmpty() ? "Plains" : colorLands.get(0);
        List<String> lands = new ArrayList<>(colorLands);
        for (int i = 0; i < generic; i++) {
            lands.add(genericFiller);
        }
        return lands;
    }
}
