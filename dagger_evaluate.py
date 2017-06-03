#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tensorflow as tf
import numpy as np
import random
import sys

from dagger_policy_generators import SmashNet
from scene_loader import THORDiscreteEnvironment as Environment

from utils.ops import sample_action

from dagger_constants import ACTION_SIZE, CHECKPOINT_DIR, NUM_EVAL_EPISODES, VERBOSE, TASK_TYPE, TEST_TASK_LIST, ENCOURAGE_SYMMETRY

def _flip_policy(policy):
    flipped_policy = np.array([policy[3],
                     policy[2],
                     policy[1],
                     policy[0]])
    return flipped_policy
    
if __name__ == '__main__':

  device = "/cpu:0" # use CPU for display tool
  network_scope = TASK_TYPE
  list_of_tasks = TEST_TASK_LIST
  scene_scopes = list_of_tasks.keys()

  global_network = SmashNet(action_size=ACTION_SIZE,
                                        device=device,
                                        network_scope=network_scope,
                                        scene_scopes=scene_scopes)

  sess = tf.Session()
  init = tf.global_variables_initializer()
  sess.run(init)

  saver = tf.train.Saver()
  checkpoint = tf.train.get_checkpoint_state(CHECKPOINT_DIR)

  if checkpoint and checkpoint.model_checkpoint_path:
    saver.restore(sess, checkpoint.model_checkpoint_path)
    print("checkpoint loaded: {}".format(checkpoint.model_checkpoint_path))
  else:
    print("Could not find old checkpoint")

  for scene_scope in scene_scopes:

    for task_scope in list_of_tasks[scene_scope]:

      env = Environment({
        'scene_name': scene_scope,
        'terminal_state_id': int(task_scope)
      })
      ep_lengths = []
      ep_collisions = []
      oracle_lengths = []
      ep_successes = []

      scopes = [network_scope, scene_scope, task_scope]

      for i_episode in range(NUM_EVAL_EPISODES):

        env.reset()
        oracle_lengths.append(env.shortest_path_distances[env.current_state_id][env.terminal_state_id])
        terminal = False
        ep_length = 0
        ep_collision = 0

        while not terminal:
          
          flipped_run = ENCOURAGE_SYMMETRY and np.random.random() > 0.5
          
          if flipped_run: pi_values = _flip_policy(global_network.run_policy(sess, env.target, env.s_t, scopes))
          else: pi_values = global_network.run_policy(sess, env.s_t, env.target, scopes)         
          action = sample_action(pi_values)
          env.step(action)
          env.update()

          terminal = env.terminal
          if ep_length == 10000: break
          if env.collided: ep_collision += 1
          ep_length += 1
        print("Episode length : %d" % ep_length)
        ep_lengths.append(ep_length)
        ep_collisions.append(ep_collision)
        ep_successes.append(int(ep_length  < 500))      

      print('Evaluation: %s %s' % (scene_scope, task_scope))
      print('Episode Lengths\n Mean: %.2f, Stddev: %.2f' % (np.mean(ep_lengths), np.std(ep_lengths)))
      print('Episode Collisions\n Mean: %.2f, Stddev: %.2f' % (np.mean(ep_collisions), np.std(ep_collisions)))
      print('Oracle Lengths\n Mean: %.2f, Stddev: %.2f' % (np.mean(oracle_lengths), np.std(oracle_lengths)))
      print('Success Rate\n Mean: %.2f' % (np.mean(ep_successes)))
      print('\n')
