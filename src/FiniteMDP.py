'''
TO DO cannot assume it is a NextStateEnv but support a general env. In
compute_optimal_action_values and others need to pass as parameters.

This class implements a finite MDP for tabular RL. It is very general
in the sense that it represents internally rewards, actions and states
as natural numbers. For instance, if a grid-world has actions "left",
"right", "up", "down", they must be mapped to integers such as 0, 1, 2 and 3.
Only the environment that extends this class will have knowledge about
the labels "left", "right", "up", "down". 

It has an environment, which is a gym env with spaces.Discrete() for both
states (called observations in gym) and actions.

In case we want to use the labels of states and actions, we need extra
information, provided e.g. by stateListGivenIndex and actionListGivenIndex.

Using powerful Python features, it's easy for an environment to
convert back and forth the representations of rewards, actions and states
into these integers using bidirectional data structures based on hash tables.
For example, one can use https://pypi.org/project/bidict/ and save storage space
by not duplicating entries. Or, because we have integers as one key, one can use
a dict and a list, instead of a bidict, which is what is implemented now.
'''
from __future__ import print_function
import numpy as np
from builtins import print
# from scipy.stats import rv_discrete
from random import choices
#from akpy.NextStateProbabilitiesEnv import NextStateProbabilitiesEnv
from NextStateProbabilitiesEnv import NextStateProbabilitiesEnv
import gym
from gym import spaces

class FiniteMDP:
    def __init__(self, environment: gym.Env):
        self.__version__ = "0.1.1"
        # print("AK Finite MDP - Version {}".format(self.__version__))

        #checks if env is a gym with discrete spaces
        assert isinstance(environment.action_space, spaces.Discrete)
        assert isinstance(environment.observation_space, spaces.Discrete)        

        self.environment = environment
        self.S = environment.observation_space.n
        self.A = environment.action_space.n

        self.currentObservation = 0
        self.currentIteration = 0
        self.environment.reset()

    def prettyPrintValues(self, action_values, stateListGivenIndex, actionListGivenIndex):
        '''
        AK-TODO: in fact we are not printing a "policy" here, but the action values.
        I guess a policy cannot be described by a table.
        :param action_values:
        :return:
        '''
        for s in range(self.S):
            currentState = stateListGivenIndex[s]
            print('\ns=', s, '=', currentState)  # ' ',end='')
            for a in range(self.A):
                if action_values[s, a] == 0:
                    continue
                currentAction = actionListGivenIndex[a]
                print(' | a=', a, '=', currentAction, end='')

    def getEquiprobableRandomPolicy(self):
        policy = np.zeros((self.S, self.A))
        uniformProbability = 1.0 / self.A
        for s in range(self.S):
            for a in range(self.A):
                policy[s, a] = uniformProbability
        return policy

    '''
    A policy is provided.
    '''
    def compute_state_values(self, policy, in_place=False, discountGamma = 0.9):
        '''Iterative policy evaluation. Page 75 of [Sutton, 2018]'''
        S = self.S
        A = self.A
        #(S, A, nS) = self.environment.nextStateProbability.shape
        # A = len(actionListGivenIndex)
        new_state_values = np.zeros((S,))
        state_values = new_state_values.copy()
        iteration = 1
        while True:
            src = new_state_values if in_place else state_values
            for s in range(S):
                value = 0
                for a in range(A):
                    if policy[s, a] == 0:
                        continue  # save computation
                    for nexts in range(S):
                        p = self.environment.nextStateProbability[s, a, nexts]
                        r = self.environment.rewardsTable[s, a, nexts]
                        value += policy[s, a] * p * (r + discountGamma * src[nexts])
                        # value += p*(r+discount*src[nexts])
                new_state_values[s] = value
            # AK-TODO, Sutton, end of pag. 75 uses the max of individual entries, while
            # here we are using the summation:
            improvement = np.sum(np.abs(new_state_values - state_values))
            # print('improvement =', improvement)
            if False:  # debug
                print('state values=', state_values)
                print('new state values=', new_state_values)
                print('it=', iteration, 'improvement = ', improvement)
            if improvement < 1e-4:
                state_values = new_state_values.copy()
                break

            state_values = new_state_values.copy()
            iteration += 1

        return state_values, iteration

    '''
    A policy is not provided.
    '''
    def compute_optimal_state_values(self, discountGamma = 0.9):
        '''Page 63 of [Sutton, 2018], Eq. (3.19)'''
        S = self.S
        A = self.A
        #(S, A, nS) = self.environment.nextStateProbability.shape
        # A = len(actionListGivenIndex)
        new_state_values = np.zeros((S,))
        state_values = new_state_values.copy()
        iteration = 1
        while True:
            for s in range(S):
                a_candidates = list()
                for a in range(A):
                    value = 0
                    for nexts in range(S):
                        p = self.environment.nextStateProbability[s, a, nexts]
                        r = self.environment.rewardsTable[s, a, nexts]
                        value += p * (r + discountGamma * state_values[nexts])
                    a_candidates.append(value)
                new_state_values[s] = np.max(a_candidates)
            improvement = np.sum(np.abs(new_state_values - state_values))
            # print('improvement =', improvement)
            if False:  # debug
                print('state values=', state_values)
                print('new state values=', new_state_values)
                print('it=', iteration, 'improvement = ', improvement)

            state_values = new_state_values.copy()
            if improvement < 1e-4:
                break

            iteration += 1

        return state_values, iteration

    def compute_optimal_action_values(self, discountGamma = 0.9):
        '''Page 64 of [Sutton, 2018], Eq. (3.20)'''
        S = self.S
        A = self.A
        #(S, A, nS) = self.environment.nextStateProbability.shape
        # A = len(actionListGivenIndex)
        new_action_values = np.zeros((S, A))
        action_values = new_action_values.copy()
        iteration = 1
        while True:
            # src = new_action_values if in_place else action_values
            for s in range(S):
                for a in range(A):
                    value = 0
                    for nexts in range(S):
                        p = self.environment.nextStateProbability[s, a, nexts]
                        r = self.environment.rewardsTable[s, a, nexts]
                        # print('amor', r, p, src[nexts])
                        best_a = -np.Infinity
                        for nexta in range(A):
                            temp = action_values[nexts, nexta]
                            if temp > best_a:
                                best_a = temp
                        value += p * (r + discountGamma * best_a)
                        # value += p*(r+discount*src[nexts])
                        # print('aa', value)
                    new_action_values[s, a] = value
            improvement = np.sum(np.abs(new_action_values - action_values))
            # print('improvement =', improvement)
            if False:  # debug
                print('state values=', action_values)
                print('new state values=', new_action_values)
                print('it=', iteration, 'improvement = ', improvement)
            if improvement < 1e-4:
                action_values = new_action_values.copy()
                break

            action_values = new_action_values.copy()
            iteration += 1

        return action_values, iteration

    def convert_action_values_into_policy(self, action_values):
        (S, A) = action_values.shape
        policy = np.zeros((S, A))
        for s in range(S):
            maxPerState = max(action_values[s])
            maxIndices = np.where(action_values[s] == maxPerState)
            # maxIndices is a tuple and we want to get first element maxIndices[0]
            policy[s, maxIndices] = 1.0 / len(maxIndices[0])  # impose uniform distribution
        return policy

    def postprocessing_MDP_step(self, history, printPostProcessingInfo):
        '''This method can be overriden by subclass and process history'''
        pass  # no need to do anything here

    def run_MDP_for_given_policy(self, policy, maxNumIterations=100, printInfo=False, printPostProcessingInfo=False):
        self.environment.reset()
        s = self.environment.get_state()
        totalReward = 0
        #if printInfo:
            #print('Initial state = ', self.stateListGivenIndex[s])
        for it in range(maxNumIterations):
            myweights = np.squeeze(policy[s])
            sumWeights = np.sum(myweights) #AK-TODO: what if there are positive and negative numbers canceling out?
            if sumWeights == 0:
                myweights = np.ones(myweights.shape)
            if True:
                #AK-TODO the choices is giving troubles with negative weights. Make them all positive
                #AK-TODO this changes the relative importances / weights, right?
                minWeight = np.min(myweights)
                if minWeight < 0:
                    myweights += (-minWeight)+1e-30
                sumWeights = np.sum(myweights)
                myweights /= sumWeights
            action = choices(np.arange(self.A), weights=myweights, k=1)[0]
            ob, reward, gameOver, history = self.environment.step(action)

            #AK
            if reward < -5:
                print(history)

            self.postprocessing_MDP_step(history, printPostProcessingInfo)
            if printInfo:
                print(history)
            totalReward += reward
            s = self.environment.get_state()
            if gameOver == True:
                break
        if printInfo:
            print('totalReward = ', totalReward)

    # an episode with Q-Learning
    # @stateActionValues: values for state action pair, will be updated
    # @expected: if True, will use expected Sarsa algorithm
    # @stepSize: step size for updating
    # @return: total rewards within this episode
    def q_learning(self, stateActionValues, maxNumIterationsQLearning=100, stepSizeAlpha=0.1,
                   explorationProbEpsilon=0.01, discountGamma = 0.9):
        currentState = self.environment.get_state()
        rewards = 0.0
        for numIterations in range(maxNumIterationsQLearning):
            currentAction = self.chooseAction(currentState, stateActionValues, explorationProbEpsilon)

            ob, reward, gameOver, history = self.environment.step(currentAction)
            newState = self.environment.get_state()
            reward = self.environment.rewardsTable[currentState, currentAction, newState]
            #reward = self.environment.get_current_reward()
            rewards += reward
            # Q-Learning update
            stateActionValues[currentState, currentAction] += stepSizeAlpha * (
                    reward + discountGamma * np.max(stateActionValues[newState, :]) -
                    stateActionValues[currentState, currentAction])
            currentState = newState
        # normalize rewards to facilitate comparison
        return rewards / maxNumIterationsQLearning

    # choose an action based on epsilon greedy algorithm
    def chooseAction(self, state, stateActionValues, explorationProbEpsilon=0.01):
        #print(state)
        if np.random.binomial(1, explorationProbEpsilon) == 1:
            return np.random.choice(np.arange(self.A))
        else:
            values_ = stateActionValues[state, :]
            return np.random.choice([action_ for action_, value_ in enumerate(values_) if value_ == np.max(values_)])

    def execute_q_learning(self, maxNumIterations=100, maxNumIterationsQLearning=10, num_runs=1,
                           stepSizeAlpha=0.1, explorationProbEpsilon=0.01):
        '''Use independent runs instead of a single run.
        maxNumIterationsQLearning is used to smooth numbers'''

        rewardsQLearning = np.zeros(maxNumIterations)
        for run in range(num_runs):
            stateActionValues = np.zeros((self.S, self.A))
            for i in range(maxNumIterations):
                # update stateActionValues in-place
                reward = self.q_learning(stateActionValues,
                                         maxNumIterationsQLearning=maxNumIterationsQLearning,
                                         stepSizeAlpha=stepSizeAlpha,
                                         explorationProbEpsilon=explorationProbEpsilon)
                rewardsQLearning[i] += reward
            print('rewardsQLearning[i]', rewardsQLearning[i]) #AK
        rewardsQLearning /= num_runs
        if False:
            print('rewardsQLearning = ', rewardsQLearning)
            print('newStateActionValues = ', stateActionValues)
            # qlearning_policy = self.convert_action_values_into_policy(newStateActionValues)
            print('qlearning_policy = ', self.prettyPrintPolicy(stateActionValues))
        return stateActionValues, rewardsQLearning

def test_with_NextStateProbabilitiesEnv():
    S = 3
    A = 2
    nextStateProbability = np.random.rand(S,A,S) #positive numbers
    rewardsTable = np.random.randn(S,A,S) #can be negative
    environment = NextStateProbabilitiesEnv(nextStateProbability, rewardsTable)
    mdp = FiniteMDP(environment) #, S, A, discount=0.9)
    stateActionValues, rewardsQLearning = mdp.execute_q_learning(maxNumIterationsQLearning=1000)
    print("stateActionValues=",stateActionValues)
    print("rewardsQLearning=",rewardsQLearning)

if __name__ == '__main__':
    test_with_NextStateProbabilitiesEnv()