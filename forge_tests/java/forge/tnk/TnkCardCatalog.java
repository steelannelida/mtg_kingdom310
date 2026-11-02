package forge.tnk;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

/**
 * Reads the exported Forge card scripts (forge_export/cards/*.txt, produced by
 * generate_forge.py from cards/*.yaml) so tests can be data-driven off "every TNK
 * card that has a forge: block" instead of hand-listing card names.
 *
 * Path to forge_export/ is relative to the Maven working directory (forge-gui-desktop/),
 * two levels up from forge-src/ into the Tales MTG Set repo -- override with
 * -Dtnk.exportDir=/absolute/path if your checkout isn't laid out that way.
 */
public final class TnkCardCatalog {
    private static final Path EXPORT_DIR = Paths.get(
            System.getProperty("tnk.exportDir", "../../forge_export/cards"));

    private TnkCardCatalog() {
    }

    public static final class ExportedCard {
        public final String name;
        public final String manaCost;   // Forge format, e.g. "2 G G", "no cost"
        public final String types;      // raw Types: value, e.g. "Creature Human Peasant"
        public final Integer power;     // null if no PT: line, or PT wasn't a plain N/N
        public final Integer toughness;
        public final boolean hasTrigger;   // any T: line
        public final boolean hasActivated; // any A: line

        ExportedCard(String name, String manaCost, String types, Integer power, Integer toughness,
                boolean hasTrigger, boolean hasActivated) {
            this.name = name;
            this.manaCost = manaCost;
            this.types = types;
            this.power = power;
            this.toughness = toughness;
            this.hasTrigger = hasTrigger;
            this.hasActivated = hasActivated;
        }

        public boolean isCreature() {
            return types != null && types.contains("Creature");
        }

        public boolean hasNoAbilities() {
            return !hasTrigger && !hasActivated;
        }
    }

    /** @return every card found under forge_export/cards/, or empty if the directory can't be read. */
    public static List<ExportedCard> loadAll() {
        List<ExportedCard> result = new ArrayList<>();
        if (!Files.isDirectory(EXPORT_DIR)) {
            return result;
        }
        try (Stream<Path> files = Files.list(EXPORT_DIR)) {
            for (Path file : (Iterable<Path>) files.filter(p -> p.toString().endsWith(".txt"))::iterator) {
                ExportedCard card = parseOne(file);
                if (card != null) {
                    result.add(card);
                }
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return result;
    }

    private static ExportedCard parseOne(Path file) throws IOException {
        String name = null, manaCost = null, types = null, pt = null;
        boolean hasTrigger = false, hasActivated = false;

        for (String line : Files.readAllLines(file)) {
            if (line.startsWith("Name:")) {
                name = line.substring("Name:".length());
            } else if (line.startsWith("ManaCost:")) {
                manaCost = line.substring("ManaCost:".length());
            } else if (line.startsWith("Types:")) {
                types = line.substring("Types:".length());
            } else if (line.startsWith("PT:")) {
                pt = line.substring("PT:".length());
            } else if (line.startsWith("T:")) {
                hasTrigger = true;
            } else if (line.startsWith("A:")) {
                hasActivated = true;
            }
            // ALTERNATE (DFC back face) sections aren't handled here -- this catalog
            // only covers front-face-only cards for now.
        }
        if (name == null) {
            return null; // not a card script we recognize (e.g. a token file)
        }

        Integer power = null, toughness = null;
        if (pt != null) {
            String[] parts = pt.split("/", 2);
            if (parts.length == 2) {
                try {
                    power = Integer.parseInt(parts[0].trim());
                    toughness = Integer.parseInt(parts[1].trim());
                } catch (NumberFormatException e) {
                    // */* or other non-numeric PT -- leave both null, callers skip these
                }
            }
        }

        return new ExportedCard(name, manaCost, types, power, toughness, hasTrigger, hasActivated);
    }
}
