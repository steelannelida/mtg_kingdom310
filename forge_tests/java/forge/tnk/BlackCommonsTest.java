package forge.tnk;

import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;

/**
 * Dedicated tests for the black commons whose forge: block has a T: or A: line --
 * i.e. the ones VanillaCreatureResolutionTest's data provider deliberately excludes
 * because their SVar-referenced logic is only parsed/exercised when actually fired.
 */
public class BlackCommonsTest extends TnkCardTestBase {

    @Test
    public void navka_diesTriggerDrainsOpponent() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        int p2LifeBefore = p2.getLife();

        Card navka = addCard("Navka", p1);
        kill(game, navka);

        assertEquals(p2.getLife(), p2LifeBefore - 1, "Each opponent should lose 1 life when Navka dies");
    }

    @Test
    public void upyr_etbCostsLifeAndCantBlock() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        int lifeBefore = p1.getLife();

        Card upyr = castFromHand(game, p1, "Upyr", "Swamp", 2);

        assertEquals(p1.getLife(), lifeBefore - 1, "Upyr's ETB should have cost 1 life");
        assertFalse(forge.game.combat.CombatUtil.canBlock(upyr), "Upyr shouldn't be able to block");
    }

    @Test
    public void nochnayaMara_etbShrinksOpponentCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);

        Card bear = addCard("Grizzly Bears", p2); // 2/2, a legal target for the ETB
        castFromHand(game, p1, "Nochnaya Mara", "Swamp", 3);

        assertEquals(bear.getNetPower(), 0, "Opponent's creature should be at -2/-0 until Nochnaya Mara's controller's next turn");
    }

    @Test
    public void kikimora_etbMakesTargetDiscard() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        addCardToZone("Plains", p2, ZoneType.Hand); // give p2 something to discard
        int p2HandBefore = p2.getCardsIn(ZoneType.Hand).size();

        castFromHand(game, p1, "Kikimora", "Swamp", 3);

        assertTrue(p2.getCardsIn(ZoneType.Hand).size() < p2HandBefore,
                "Target player's hand should have shrunk from Kikimora's discard ETB");
    }

    @Test
    public void starukhaVedma_activatedAbilityShrinksTarget() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);

        Card starukha = addCard("Starukha-Vedma", p1);
        starukha.setSickness(false); // it has a {T} ability; addCard alone leaves it summoning-sick
        addCards("Swamp", 2, p1); // {1}{B} activation cost
        Card bear = addCard("Grizzly Bears", p2);

        activateAbility(game, p1, starukha, "{1}{B}, {T}: Target creature gets -1/-1", bear);

        assertEquals(bear.getNetPower(), 1, "Target should be -1/-1 until end of turn");
        assertEquals(bear.getNetToughness(), 1, "Target should be -1/-1 until end of turn");
    }

    @Test
    public void kladbishchenskiyStorozh_activatedAbilityExilesFromGraveyard() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);

        Card storozh = addCard("Kladbishchenskiy Storozh", p1);
        storozh.setSickness(false); // it has a {T} ability; addCard alone leaves it summoning-sick
        Card inGrave = addCardToZone("Grizzly Bears", p2, ZoneType.Graveyard);

        activateAbility(game, p1, storozh, "{T}: Exile target card from a graveyard", inGrave);

        assertTrue(inGrave.isInZone(ZoneType.Exile), "Targeted graveyard card should have been exiled");
    }
}
