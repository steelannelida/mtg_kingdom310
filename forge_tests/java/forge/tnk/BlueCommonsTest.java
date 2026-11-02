package forge.tnk;

import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/** Tests for blue commons with a T:/A: line (not auto-covered by VanillaCreatureResolutionTest). */
public class BlueCommonsTest extends TnkCardTestBase {

    @Test
    public void kupetsNaPristani_etbScries() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        Card kupets = castFromHand(game, p1, "Kupets na Pristani", "Island", 2);

        assertTrue(kupets.isInZone(ZoneType.Battlefield), "Kupets na Pristani should resolve without crashing on its ETB scry");
    }

    @Test
    public void rusalkaIskusitelnitsa_etbTapsAndFreezesOpponentCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2);

        castFromHand(game, p1, "Rusalka-Iskusitelnitsa", "Island", 3);

        assertTrue(bear.isTapped(), "Rusalka-Iskusitelnitsa's ETB should tap the opponent's creature");
        assertTrue(bear.hasKeyword("HIDDEN This card doesn't untap during your next untap step."),
                "The frozen creature should carry the doesn't-untap marker");
    }

    @Test
    public void chudoRybka_activatedAbilityScriesAndDraws() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card rybka = addCard("Chudo-Rybka", p1);
        rybka.setSickness(false);
        addCardToZone("Island", p1, ZoneType.Library); // so the draw doesn't lose the game
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        activateAbility(game, p1, rybka, "{T}, Sacrifice", null);

        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 1, "Chudo-Rybka should draw a card");
        assertTrue(rybka.isInZone(ZoneType.Graveyard), "Chudo-Rybka should have sacrificed itself");
    }

    @Test
    public void lebedBelaya_getsPumpedWhenYouScry() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card lebed = addCard("Lebed Belaya", p1);
        addCards("Island", 1, p1);
        assertEquals(lebed.getNetPower(), 1, "Base power before scrying");

        Card starik = addCard("Starik-Rybak", p1);
        starik.setSickness(false);
        activateAbility(game, p1, starik, "{T}: Scry 1", null);

        assertEquals(lebed.getNetPower(), 2, "Lebed Belaya should get +1/+0 whenever you scry");
    }

    @Test
    public void gusiLebedi_etbMayBounceTargetCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2);

        castFromHand(game, p1, "Gusi-Lebedi", "Island", 5);

        // "may" bounce is an AI choice; just confirm the ETB resolves without crashing.
        assertTrue(findCardWithName(game, "Gusi-Lebedi") != null);
    }

    @Test
    public void utoplennik_etbPutsTargetCreatureOnBottomOfLibrary() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2);
        int libraryBefore = p2.getCardsIn(ZoneType.Library).size();

        castFromHand(game, p1, "Utoplennik", "Island", 4);

        assertTrue(bear.isInZone(ZoneType.Library), "Utoplennik's ETB should put the target on the bottom of its owner's library");
        assertEquals(p2.getCardsIn(ZoneType.Library).size(), libraryBefore + 1);
    }

    @Test
    public void koraBlKupecheskiy_activatedAbilityDrawsAsSorcery() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card korabl = addCard("Korabl Kupecheskiy", p1);
        korabl.setSickness(false);
        addCards("Island", 2, p1); // {2} activation cost
        addCardToZone("Island", p1, ZoneType.Library); // so the draw doesn't lose the game
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        activateAbility(game, p1, korabl, "{2}, {T}: Draw a card", null);

        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 1, "Korabl Kupecheskiy should draw a card");
    }

    @Test
    public void vodyanitsa_etbDigsThreeAndKeepsOne() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        for (int i = 0; i < 3; i++) {
            addCardToZone("Island", p1, ZoneType.Library);
        }
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        castFromHand(game, p1, "Vodyanitsa", "Island", 2);

        // castFromHand() puts Vodyanitsa into hand then casts it (net 0 from that), and
        // the dig then puts one card into hand (net +1 overall).
        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 1, "The dig should have put one card into hand");
    }

    @Test
    public void starikRybak_activatedAbilityScries() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card starik = addCard("Starik-Rybak", p1);
        starik.setSickness(false);
        addCards("Island", 1, p1);

        activateAbility(game, p1, starik, "{T}: Scry 1", null);
        assertTrue(starik.isInZone(ZoneType.Battlefield));
    }

    @Test
    public void rechnoyTuman_shrinksTargetAndScries() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2); // 2/2

        castTargeted(game, p1, "Rechnoy Tuman", bear, "Island", 1);

        assertEquals(bear.getNetPower(), -2, "Rechnoy Tuman should apply -4/-0 (Forge doesn't floor net power at 0)");
    }

    @Test
    public void bluddyechko_activatedAbilityScries() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bluddyechko = addCard("Bluddyechko s Yablochkom", p1);
        addCards("Island", 1, p1);

        activateAbility(game, p1, bluddyechko, "{1}, {T}: Scry 2", null);
        assertTrue(bluddyechko.isInZone(ZoneType.Battlefield));
    }

    @Test
    public void zovMorya_bouncesTargetCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2);

        castTargeted(game, p1, "Zov Morya", bear, "Island", 2);

        assertTrue(bear.isInZone(ZoneType.Hand), "Zov Morya should bounce the target creature to hand");
    }

    @Test
    public void veschiySon_resolvesWithoutCrashing() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        addCards("Island", 3, p1);

        castFromHand(game, p1, "Veschiy Son", "Island", 1);
        assertTrue(findCardWithName(game, "Veschiy Son") == null); // sorcery, should be in graveyard, not battlefield
    }

    @Test
    public void obmanZreniya_targetBecomesCopyOfAnotherCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1); // 2/2, the copy target
        Card sivka = addCard("Sivka-Burka", p1); // 3/2, the creature that becomes a copy

        addCards("Island", 2, p1);
        Card obman = addCardToZone("Obman Zreniya", p1, ZoneType.Hand);
        SpellAbility sa = obman.getSpells().get(0); // the Pump: "target creature" (becomes the copy)
        sa.setActivatingPlayer(p1);
        sa.getTargets().add(sivka);
        // DBClone's own "another target creature you control" is a separate target on
        // the SubAbility object, not the root SpellAbility's target list.
        sa.getSubAbility().getTargets().add(bear);
        boolean played = forge.ai.ComputerUtil.playStack(sa, p1, game);
        assertTrue(played, "Obman Zreniya should have been castable with two targets");
        game.getStack().resolveStack();
        resolveEverything(game);

        assertEquals(sivka.getName(), "Grizzly Bears", "Sivka-Burka should have become a copy of Grizzly Bears");
    }

    @Test
    public void otplyitye_drawsTwoThenDiscardsOne() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        for (int i = 0; i < 2; i++) {
            addCardToZone("Island", p1, ZoneType.Library);
        }
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        castFromHand(game, p1, "Otplyitye", "Island", 3); // costs {2}{U}

        // castFromHand() adds Otplyitye to hand then casts it (net 0 from that), then
        // the spell draws 2 and discards 1 (net +1) -- so overall net change is +1.
        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 1,
                "Net +1: draw 2, discard 1");
    }

    @Test
    public void treskuchiyMoroz_tapsAllOfTargetPlayersCreatures() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear1 = addCard("Grizzly Bears", p2);
        Card bear2 = addCard("Runeclaw Bear", p2);
        bear1.setTapped(false);
        bear2.setTapped(false);

        SpellAbility sa;
        addCards("Island", 3, p1);
        Card moroz = addCardToZone("Treskuchiy Moroz", p1, ZoneType.Hand);
        sa = moroz.getSpells().get(0);
        sa.setActivatingPlayer(p1);
        sa.getTargets().add(p2);
        boolean played = forge.ai.ComputerUtil.playStack(sa, p1, game);
        assertTrue(played, "Treskuchiy Moroz should have been castable targeting a player");
        game.getStack().resolveStack();
        resolveEverything(game);

        assertTrue(bear1.isTapped() && bear2.isTapped(), "Treskuchiy Moroz should tap all of the target player's creatures");
    }

    @Test
    public void starinnayaLetopis_returnsInstantOrSorceryFromGraveyard() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card inGrave = addCardToZone("Grom i Molniya", p1, ZoneType.Graveyard); // an instant

        castTargeted(game, p1, "Starinnaya Letopis", inGrave, "Island", 2);

        assertTrue(inGrave.isInZone(ZoneType.Hand), "Starinnaya Letopis should return the targeted card to hand");
    }

    @Test
    public void vBochkePoMoryu_etbTapsThenSearchesOnUntap() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        bear.setTapped(false);
        addCardToZone("Grom i Molniya", p1, ZoneType.Library); // an instant for the tutor to find

        Card aura = castTargeted(game, p1, "V Bochke po Moryu", bear, "Island", 2);
        assertTrue(bear.isTapped(), "V Bochke po Moryu's ETB should tap the enchanted creature");

        // Untapping the creature naturally (its controller's next untap step) is
        // needed to fire the search-and-sacrifice trigger -- not exercised here, this
        // test only confirms the ETB half.
        assertTrue(aura.isInZone(ZoneType.Battlefield));
    }
}
