(() => {
    "use strict";

    const LEVELS = Object.freeze(["100", "200", "300", "400", "Final Year", "Graduate Mix"]);
    const AI_ML = "AI/ML";
    const PRO = "Pro";
    const MAX_ROUND_SIZE = 20;
    const TIE_LIMIT = 3;

    function shuffle(items, random = Math.random) {
        const shuffled = [...items];
        for (let index = shuffled.length - 1; index > 0; index -= 1) {
            const swapIndex = Math.floor(random() * (index + 1));
            [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
        }
        return shuffled;
    }

    function roundDraws(level, count, random) {
        if (!Number.isInteger(count) || count < 1 || count > MAX_ROUND_SIZE) {
            throw new RangeError(`Round length must be a whole number from 1 to ${MAX_ROUND_SIZE}`);
        }
        if (level === PRO) {
            // Round the cumulative cutoffs with one offset so the quotas always sum to count.
            const offset = Math.floor(random() * 10);
            const advanced = Math.floor((7 * count + offset) / 10);
            const advancedAndBonus = Math.floor((9 * count + offset) / 10);
            return [
                [LEVELS.slice(3), advanced],
                [[AI_ML], advancedAndBonus - advanced],
                [LEVELS.slice(0, 3), count - advancedAndBonus],
            ];
        }
        if (level === AI_ML) {
            return [[[AI_ML], count]];
        }

        const levelIndex = LEVELS.indexOf(level);
        if (levelIndex === -1) {
            throw new RangeError(`Unknown level ${level}`);
        }
        const review = levelIndex === 0 ? 0 : Math.floor((count + 2) / 5);
        return [[[level], count - review], [LEVELS.slice(0, levelIndex), review]];
    }

    function drawSolo(bank, level, count, random = Math.random) {
        const questions = [];
        for (const [sources, quota] of roundDraws(level, count, random)) {
            if (quota === 0) continue;
            const pool = bank.filter((item) => sources.includes(item.level));
            if (pool.length < quota) {
                throw new RangeError(`${sources.join(", ")} has ${pool.length} questions, needs ${quota}`);
            }
            questions.push(...shuffle(pool, random).slice(0, quota));
        }
        return shuffle(questions, random);
    }

    function pairPool(bank, source, random) {
        const groups = new Map();
        for (const question of bank) {
            if (question.level !== source) continue;
            const group = `${question.difficulty}:${question.clue_type}`;
            const concept = question.concept.trim().toLowerCase();
            if (!groups.has(group)) groups.set(group, new Map());
            const concepts = groups.get(group);
            if (!concepts.has(concept)) concepts.set(concept, []);
            concepts.get(concept).push(question);
        }

        const pairs = [];
        for (const concepts of groups.values()) {
            let pools = Array.from(concepts.values(), (pool) => shuffle(pool, random));
            while (pools.length >= 2) {
                // Pair the two largest concept groups to preserve the maximum number of pairs.
                pools = shuffle(pools, random).sort((left, right) => right.length - left.length);
                pairs.push(shuffle([pools[0].pop(), pools[1].pop()], random));
                pools = pools.filter((pool) => pool.length > 0);
            }
        }
        return pairs;
    }

    function drawPairs(bank, level, count, random = Math.random) {
        const regular = [];
        const reserve = [];
        const draws = roundDraws(level, count, random);
        for (const [index, [sources, quota]] of draws.entries()) {
            const needed = quota + (index === 0 ? TIE_LIMIT : 0);
            if (needed === 0) continue;
            const pool = sources.flatMap((source) => pairPool(bank, source, random));
            if (pool.length < needed) {
                throw new RangeError(`${sources.join(", ")} has ${pool.length} matched pairs, needs ${needed}`);
            }
            const selected = shuffle(pool, random).slice(0, needed);
            regular.push(...selected.slice(0, quota));
            reserve.push(...selected.slice(quota));
        }
        return [...shuffle(regular, random), ...reserve];
    }

    function regulationScore(outcomes, count) {
        let correct = 0;
        let elapsed = 0;
        for (const outcome of outcomes.slice(0, count)) {
            if (outcome.correct) {
                correct += 1;
                elapsed += outcome.elapsed;
            }
        }
        return { correct, elapsed };
    }

    function matchWinner([left, right], count) {
        const completed = Math.min(left.length, right.length);
        if (completed < count) return null;

        const leftScore = regulationScore(left, count);
        const rightScore = regulationScore(right, count);
        if (leftScore.correct !== rightScore.correct) {
            return leftScore.correct > rightScore.correct ? 0 : 1;
        }
        const leftAverage = leftScore.elapsed * rightScore.correct;
        const rightAverage = rightScore.elapsed * leftScore.correct;
        if (leftAverage !== rightAverage) {
            return leftAverage < rightAverage ? 0 : 1;
        }

        const end = Math.min(completed, count + TIE_LIMIT);
        for (let index = count; index < end; index += 1) {
            if (left[index].correct !== right[index].correct) {
                return left[index].correct ? 0 : 1;
            }
        }
        return end === count + TIE_LIMIT ? "draw" : null;
    }

    globalThis.QuizRules = { LEVELS, drawSolo, drawPairs, shuffle, matchWinner };
})();
