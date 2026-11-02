package forge.tnk;

import forge.game.Game;
import forge.game.player.Player;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;

/**
 * Tests for TNK cards whose ability fires as a triggered ability (ETBs, etc), which
 * needs a full stack-resolution loop, not just one resolveStack() call -- see
 * TnkCardTestBase.resolveStackFully().
 */
public class TnkTriggeredAbilityTest extends TnkCardTestBase {

    @Test
    public void kalikaPerekhozhiy_etbGainsTwoLife() {
        // Kalika Perekhozhiy (1W, 1/3 Human Cleric):
        // "When this enters the battlefield, you gain 2 life."
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        int lifeBefore = p1.getLife();

        castFromHand(game, p1, "Kalika Perekhozhiy", "Plains", 2);

        assertEquals(p1.getLife(), lifeBefore + 2,
                "Kalika Perekhozhiy's ETB should have gained 2 life");
    }
}
