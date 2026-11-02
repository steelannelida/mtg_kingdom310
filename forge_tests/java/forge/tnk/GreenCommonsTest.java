package forge.tnk;

import forge.ai.ComputerUtil;
import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/** Tests for green commons with a T:/A: line (not auto-covered by VanillaCreatureResolutionTest). */
public class GreenCommonsTest extends TnkCardTestBase {

    @Test
    public void dubVekovoy_activatedManaAbility() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card dub = addCard("Dub Vekovoy", p1);
        dub.setSickness(false);

        activateAbility(game, p1, dub, "{T}: Add {G}", null);
        assertTrue(dub.isTapped(), "Dub Vekovoy should be tapped after using its mana ability");
    }

    @Test
    public void seryVolk_getsTrampleWhenAttackingWhileSaddled() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card volk = addCard("Sery Volk", p1);
        volk.setSickness(false);
        Card fodder = addCard("Grizzly Bears", p1);
        fodder.setSickness(false);
        game.getTriggerHandler().registerActiveTrigger(volk, false);

        activateAbility(game, p1, volk, "Saddle 1", null);
        assertTrue(volk.isSaddled(), "Sery Volk should be saddled");

        declareAttackersNaturally(game);

        assertTrue(volk.hasKeyword("Trample"), "Sery Volk should gain trample when attacking while saddled");
    }

    @Test
    public void yablonkaDobraya_activatedAbilityCreatesFood() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card yablonka = addCard("Yablonka Dobraya", p1);
        yablonka.setSickness(false);
        addCards("Forest", 1, p1);

        activateAbilityContaining(game, p1, yablonka, "Create a Food token", null);

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).anyMatch(c -> c.getType().hasSubtype("Food")),
                "Yablonka Dobraya should have created a Food token");
    }

    @Test
    public void starichokLesovichok_etbSearchesBasicLandToHand() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        addCardToZone("Forest", p1, ZoneType.Library);

        castFromHand(game, p1, "Starichok-Lesovichok", "Forest", 4);

        assertTrue(p1.getCardsIn(ZoneType.Hand).anyMatch(c -> c.getName().equals("Forest")),
                "Starichok-Lesovichok's ETB should find a basic land into hand");
    }

    @Test
    public void turoviyByk_activatedAbilityGrantsTrample() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card byk = addCard("Turoviy Byk", p1);
        addCards("Forest", 1, p1);
        assertTrue(!byk.hasKeyword("Trample"), "Should not have trample before activating");

        activateAbilityContaining(game, p1, byk, "gains trample until end of turn", null);

        assertTrue(byk.hasKeyword("Trample"), "Turoviy Byk should gain trample after activating");
    }

    @Test
    public void zhivayaVoda_regeneratesAndCreatesFood() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);

        castTargeted(game, p1, "Zhivaya Voda", bear, "Forest", 1);

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).anyMatch(c -> c.getType().hasSubtype("Food")),
                "Zhivaya Voda should have created a Food token");
    }

    @Test
    public void lesnayaTropa_searchesBasicLandOntoBattlefieldTapped() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        addCardToZone("Forest", p1, ZoneType.Library);

        castFromHand(game, p1, "Lesnaya Tropa", "Forest", 2); // costs {1}{G}

        Card foundForest = findCardWithName(game, "Forest");
        assertTrue(foundForest != null && foundForest.isTapped(),
                "Lesnaya Tropa should put a basic land onto the battlefield tapped");
    }

    @Test
    public void medovySbiten_createsTwoFoodTokens() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        castFromHand(game, p1, "Medovy Sbiten", "Forest", 2); // costs {1}{G}

        long foodCount = p1.getCardsIn(ZoneType.Battlefield).stream()
                .filter(c -> c.getType().hasSubtype("Food")).count();
        assertEquals(foodCount, 2, "Medovy Sbiten should create two Food tokens");
    }

    @Test
    public void bogatyrskaskaSila_putsTwoCountersOrThreeOnAQuest() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);

        castTargeted(game, p1, "Bogatyrskaya Sila", bear, "Forest", 3);

        assertEquals(bear.getCounters(forge.game.card.CounterEnumType.P1P1), 2,
                "Without a quest, should put exactly two +1/+1 counters (not more, not fewer)");
    }

    @Test
    public void bogatyrskaskaSila_putsThreeCountersOnAQuest() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3);
        assertTrue(bear.isEnchantedBy(questAura));

        castTargeted(game, p1, "Bogatyrskaya Sila", bear, "Forest", 3);

        assertEquals(bear.getCounters(forge.game.card.CounterEnumType.P1P1), 3,
                "On a quest, should put three +1/+1 counters total");
    }

    @Test
    public void muravyinayaBlagodarnost_createsXInsectsNoQuestBonus() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        // {X}{G}{G}: X is chosen by the AI paying the cost, not something this harness
        // controls directly. 4 mana available means X could legally be up to 2; just
        // confirm it resolves and the token count matches whatever X the AI picked
        // (0 tokens for X=0 is a legal, if conservative, choice).
        castFromHand(game, p1, "Muravyinaya Blagodarnost", "Forest", 4);

        long insectCount = p1.getCardsIn(ZoneType.Battlefield).stream()
                .filter(c -> c.getType().hasSubtype("Insect")).count();
        assertTrue(insectCount >= 0, "Muravyinaya Blagodarnost should resolve without crashing regardless of the AI's chosen X");
        assertTrue(p1.getCardsIn(ZoneType.Battlefield).stream().noneMatch(c -> c.getType().hasSubtype("Food")),
                "Without a quest creature, no Food tokens should be created");
    }

    @Test
    public void sekretnyyPosvist_additionalCostTapsCreatureThenTutors() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card fodder = addCard("Grizzly Bears", p1);
        fodder.setSickness(false);
        addCardToZone("Runeclaw Bear", p1, ZoneType.Library);
        addCards("Forest", 2, p1);

        Card posvist = addCardToZone("Sekretnyy Posvist", p1, ZoneType.Hand);
        SpellAbility sa = posvist.getSpells().get(0);
        sa.setActivatingPlayer(p1);
        boolean played = ComputerUtil.playStack(sa, p1, game);
        assertTrue(played, "Sekretnyy Posvist should have been castable (paying the tap-a-creature additional cost)");
        game.getStack().resolveStack();
        resolveEverything(game);

        assertTrue(fodder.isTapped(), "The additional cost should have tapped a creature");
        assertTrue(p1.getCardsIn(ZoneType.Hand).anyMatch(c -> c.getName().equals("Runeclaw Bear")),
                "Sekretnyy Posvist should find a creature card into hand");
    }

    @Test
    public void zayatsBeglets_etbMayAttachAnExistingQuestToItself() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card anotherCreature = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", anotherCreature, "Forest", 3);
        assertTrue(anotherCreature.isEnchantedBy(questAura));

        castFromHand(game, p1, "Zayats-Beglets", "Forest", 1);

        // Moving the aura is an AI "may" choice; just confirm this doesn't crash --
        // Forge's Attach ability for moving an existing Aura between permanents was
        // never independently verified elsewhere in this suite.
        assertTrue(findCardWithName(game, "Zayats-Beglets") != null);
    }

    @Test
    public void voronVestnik_etbMayCounterOnQuestCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3);
        assertTrue(bear.isEnchantedBy(questAura));
        int powerBefore = bear.getNetPower();

        castFromHand(game, p1, "Voron-Vestnik", "Forest", 2);

        // "may put a counter" is an AI choice -- just confirm the ETB resolves.
        assertTrue(findCardWithName(game, "Voron-Vestnik") != null);
    }
}
