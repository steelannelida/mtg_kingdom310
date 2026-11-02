package forge.tnk;

import java.util.Collections;
import java.util.List;

import forge.ai.ComputerUtil;
import forge.ai.simulation.SimulationTest;
import forge.game.Game;
import forge.game.GameObject;
import forge.game.card.Card;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;

import static org.testng.Assert.assertNotNull;
import static org.testng.Assert.assertTrue;

/**
 * Shared setup for TNK per-card tests: a real Game/Player pair (no PowerMock --
 * FModel.initialize() is the real init path, which also loads
 * ForgeConstants.USER_CUSTOM_CARDS_DIR, i.e. TNK's installed cards).
 */
public abstract class TnkCardTestBase extends SimulationTest {

    protected Game newGameInMain1() {
        Game game = initAndCreateGame();
        Player p1 = game.getPlayers().get(0);
        game.getPhaseHandler().devModeSet(PhaseType.MAIN1, p1);
        return game;
    }

    /** Convenience overload for a single basic land type -- see the List overload below. */
    protected Card castFromHand(Game game, Player p, String cardName, String basicLand, int landCount) {
        return castFromHand(game, p, cardName, Collections.nCopies(landCount, basicLand));
    }

    /**
     * Puts one of each named basic land onto the battlefield (untapped), puts
     * {@code cardName} into hand, casts it (paying its real mana cost via the AI's
     * mana-payment logic against exactly those lands), and resolves the stack.
     */
    protected Card castFromHand(Game game, Player p, String cardName, List<String> basicLands) {
        for (String land : basicLands) {
            addCard(land, p);
        }
        Card card = addCardToZone(cardName, p, ZoneType.Hand);

        SpellAbility sa = card.getSpells().get(0);
        sa.setActivatingPlayer(p);
        boolean played = ComputerUtil.playStack(sa, p, game);
        assertTrue(played, cardName + " should have been payable/playable with " + basicLands);
        // Resolve the spell itself deterministically first, then resolve whatever that
        // resolution triggers (e.g. an ETB) -- see resolveEverything()'s comment for why
        // that's needed instead of AITest.playUntilStackClear().
        game.getStack().resolveStack();
        resolveEverything(game);

        Card resolved = findCardWithName(game, cardName); // AITest: searches Battlefield
        return resolved != null ? resolved : card;
    }

    /**
     * Casts a targeted spell (most commonly an Aura) from hand, manually setting its
     * target -- castFromHand() doesn't do target selection, which is fine for spells the
     * AI can legally cast untargeted-by-us, but an Aura needs a specific target chosen
     * before ComputerUtil.playStack() will accept it.
     */
    protected Card castTargeted(Game game, Player p, String cardName, GameObject target, String basicLand, int landCount) {
        addCards(basicLand, landCount, p);
        Card card = addCardToZone(cardName, p, ZoneType.Hand);
        SpellAbility sa = card.getSpells().get(0);
        sa.setActivatingPlayer(p);
        sa.getTargets().add(target);
        boolean played = ComputerUtil.playStack(sa, p, game);
        assertTrue(played, cardName + " should have been castable targeting " + target);
        game.getStack().resolveStack();
        resolveEverything(game);
        Card resolved = findCardWithName(game, cardName);
        return resolved != null ? resolved : card;
    }

    /**
     * Equips {@code equipment} (already on the battlefield) onto {@code creature} by
     * finding its native Equip ability via SpellAbility.isEquip() -- more robust than
     * matching the rendered description text, which Forge auto-generates from the K:Equip
     * cost and isn't worth hardcoding here.
     */
    protected void equip(Game game, Player p, Card equipment, Card creature) {
        SpellAbility equipSa = null;
        for (SpellAbility sa : equipment.getSpellAbilities()) {
            if (sa.isEquip()) {
                equipSa = sa;
                break;
            }
        }
        assertNotNull(equipSa, equipment.getName() + " should have an Equip ability");
        equipSa.setActivatingPlayer(p);
        equipSa.getTargets().add(creature);
        boolean played = ComputerUtil.playStack(equipSa, p, game);
        assertTrue(played, equipment.getName() + " should have been equippable onto " + creature.getName());
        game.getStack().resolveStack();
        resolveEverything(game);
    }

    /**
     * Advances the active player's turn into combat and lets the AI naturally declare
     * attackers, then resolves whatever that triggers (e.g. an attack-triggered ability).
     * Do NOT use a manually-constructed Combat object for this: confirmed by direct
     * experiment that {@code new Combat(p); combat.addAttacker(...);
     * game.getPhaseHandler().setCombat(combat);} does NOT cause Mode$ Attacks triggers to
     * fire through resolveEverything() -- only a real phase transition into
     * COMBAT_DECLARE_ATTACKERS does. The AI decides who attacks; with an empty or weak
     * opposing board this is normally everyone who can, but it's not something the test
     * controls directly the way an assigned target is.
     */
    protected void declareAttackersNaturally(Game game) {
        playUntilPhase(game, PhaseType.COMBAT_DECLARE_ATTACKERS);
        resolveEverything(game);
    }

    /** Like {@link #declareAttackersNaturally}, but for the defender's block decision. */
    protected void declareBlockersNaturally(Game game) {
        playUntilPhase(game, PhaseType.COMBAT_DECLARE_BLOCKERS);
        resolveEverything(game);
    }

    /**
     * Activates {@code source}'s ability whose description starts with {@code descriptionPrefix}
     * (see AITest.findSAWithPrefix), optionally targeting {@code target}, paying its real cost,
     * and resolves it fully (including any resulting triggered ability).
     */
    protected void activateAbility(Game game, Player p, Card source, String descriptionPrefix, GameObject target) {
        SpellAbility sa = findSAWithPrefix(source, descriptionPrefix);
        assertNotNull(sa, "No ability starting with \"" + descriptionPrefix + "\" found on " + source.getName());
        activateFoundAbility(game, p, source, descriptionPrefix, sa, target);
    }

    /**
     * Like {@link #activateAbility}, but matches by a substring found anywhere in the
     * ability's rendered description instead of a strict prefix. Useful when a cost with
     * multiple parts (e.g. a tap plus a mana cost) doesn't render in the order the card's
     * own Cost$ string lists them, which isn't consistent enough to guess a reliable
     * prefix for -- match on the effect text instead, e.g. "Create a Food token".
     */
    protected void activateAbilityContaining(Game game, Player p, Card source, String descriptionSubstring, GameObject target) {
        SpellAbility sa = null;
        for (SpellAbility candidate : source.getSpellAbilities()) {
            if (candidate.getDescription().contains(descriptionSubstring)) {
                sa = candidate;
                break;
            }
        }
        assertNotNull(sa, "No ability containing \"" + descriptionSubstring + "\" found on " + source.getName());
        activateFoundAbility(game, p, source, descriptionSubstring, sa, target);
    }

    private void activateFoundAbility(Game game, Player p, Card source, String label, SpellAbility sa, GameObject target) {
        sa.setActivatingPlayer(p);
        if (target != null) {
            sa.getTargets().add(target);
        }
        boolean played = ComputerUtil.playStack(sa, p, game);
        assertTrue(played, source.getName() + "'s \"" + label + "\" ability should have been activatable");
        // Mana abilities (rule 605) never use the stack -- they resolve immediately as
        // part of activation, so the stack can already be empty here.
        if (!game.getStack().isEmpty()) {
            game.getStack().resolveStack();
        }
        resolveEverything(game);
    }

    /**
     * Kills {@code card} outright (e.g. to test a dies-trigger) and resolves any resulting
     * trigger. A dies trigger "looks back in time" -- by the time anything checks for it,
     * the card is already gone from the battlefield -- so Forge needs two things lined up
     * to still recognize it as eligible: the trigger registered as active *while the card
     * is still on the battlefield* (addCard() puts a card straight into a zone's list,
     * skipping the real "enters the battlefield" path that would normally do this), and a
     * just-before-death snapshot (game.copyLastState()) for the "looks back in time" check
     * itself. Both are required together; either one alone silently does nothing -- the
     * death still happens, the trigger just never fires, with no error or warning.
     * Killing it via lethal damage + checkStateEffects() (rather than GameAction.destroy()
     * directly) matters too: only checkStateEffects()'s own state-based-action loop builds
     * the CardZoneTable that re-registers the trigger post-death.
     */
    protected void kill(Game game, Card card) {
        game.getTriggerHandler().registerActiveTrigger(card, false);
        game.copyLastState();
        card.setDamage(card.getNetToughness() + 1);
        game.getAction().checkStateEffects(true);
        resolveEverything(game);
    }

    /**
     * Drives the real main-loop until both the stack and Forge's simultaneous-trigger
     * holding buffer are empty. AITest.playUntilStackClear() breaks out the instant the
     * *phase* changes, which is too eager here: a triggered ability doesn't necessarily
     * get flushed from that buffer onto the (real, counted) stack within the same phase
     * it was queued in -- e.g. a dies trigger queued in MAIN1 was only actually flushed
     * and resolved after the game had already moved on to COMBAT_BEGIN. Ignoring phase
     * changes and checking both the stack and the buffer is what's actually correct here.
     *
     * Also unconditionally runs checkStateEffects() before the stack/buffer check on
     * every iteration (including when the stack was ALREADY empty going in, e.g. right
     * after game.getStack().resolveStack() resolved a single instant with no triggers):
     * MagicStack.resolveStack() itself does not check state-based actions or recompute
     * continuous-effect layers, so without this, lethal damage from a direct-damage
     * spell silently never destroys its target, and Pump/keyword-grant effects with no
     * other trigger to piggyback on (e.g. a mass anthem with no target) don't show up in
     * getNetPower()/hasKeyword() until *something else* happens to force a recompute.
     * Confirmed via Grom i Molniya (lethal damage, creature stayed alive) and Klich
     * Bogatyrskiy (mass +1/+0, power didn't change) both failing without this, and
     * passing with it.
     */
    protected void resolveEverything(Game game) {
        int maxIterations = 50;
        for (int i = 0; i < maxIterations && !game.isGameOver(); i++) {
            game.getAction().checkStateEffects(true);
            if (game.getStack().isEmpty() && !game.getStack().hasSimultaneousStackEntries()) {
                break;
            }
            game.getPhaseHandler().mainLoopStep();
        }
    }

    /**
     * Advances past declared blockers into damage actually being dealt, and resolves any
     * resulting triggers (e.g. "whenever this deals combat damage to a player"). Needed
     * on top of declareBlockersNaturally(): COMBAT_DECLARE_BLOCKERS is blockers being
     * declared, not damage -- combat damage isn't dealt until the COMBAT_DAMAGE phase.
     */
    protected void resolveCombatDamage(Game game) {
        playUntilPhase(game, PhaseType.COMBAT_DAMAGE);
        resolveEverything(game);
    }
}
