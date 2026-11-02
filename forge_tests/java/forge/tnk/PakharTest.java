package forge.tnk;

import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNotNull;
import static org.testng.Assert.assertTrue;

/**
 * Pakhar (Plowman): {W}, 1/2 Human Peasant, vanilla (forge: {} -- no ability).
 * Battlefield starts empty except the one Plains needed to pay {W}.
 */
public class PakharTest extends TnkCardTestBase {

    @Test
    public void pakhar_resolvesAsA1_2CreatureWhenCast() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        Card pakhar = castFromHand(game, p1, "Pakhar", "Plains", 1);

        assertNotNull(pakhar, "Pakhar should have resolved");
        assertTrue(pakhar.isInZone(ZoneType.Battlefield), "Pakhar should be on the battlefield after resolving");
        assertEquals(pakhar.getNetPower(), 1);
        assertEquals(pakhar.getNetToughness(), 2);
    }
}
