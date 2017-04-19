import tensorflow as tf
import os

from modules.irwin.TrainingStats import Accuracy

class MoveAnalysis:
  @staticmethod
  def combineInputs(X):
    playerandgamesfnn = tf.contrib.layers.stack(X, tf.contrib.layers.fully_connected, [40, 10, 10, 2])
    return tf.reshape(playerandgamesfnn, [-1, 2])

  @staticmethod
  def inference(X):
    return tf.nn.softmax(self.combineInputs(X))

  @staticmethod
  def loss(X, Y):
    comb = self.combineInputs(X)
    entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(comb, Y))
    predicted = tf.round(tf.nn.softmax(comb))
    evaluation = tf.reduce_mean(tf.cast(tf.equal(predicted, Y), tf.float32))
    return entropy, evaluation, tf.concat(1, [comb, predicted, Y])

  @staticmethod
  def inputs():
    inputList = self.readCSV(800, [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0]])
    features = tf.transpose(tf.pack(inputList[1:]))
    cheat = tf.to_float(tf.equal(inputList[0], [1]))
    legit = tf.to_float(tf.equal(inputList[0], [0]))
    cheating = tf.transpose(tf.pack([legit, cheat]))
    return features, cheating

  @staticmethod
  def train(totalLoss):
    learningRate = 0.001
    return tf.train.AdamOptimizer(learningRate).minimize(totalLoss)

  @staticmethod
  def evaluate(X, Y):
    with tf.name_scope("evaluate"):
      predicted = tf.cast(self.inference(X) > 0.5, tf.float32)
      return tf.reduce_mean(tf.cast(tf.equal(predicted, Y), tf.float32))

  @staticmethod
  def readCSV(batchSize, recordDefaults):
    filename_queue = tf.train.string_input_producer(['data/classified-moves.csv'])
    reader = tf.TextLineReader(skip_header_lines=1)
    key, value = reader.read(filename_queue)
    decoded = tf.decode_csv(value, record_defaults=recordDefaults)
    return tf.train.shuffle_batch(decoded,
      batch_size=batchSize,
      capacity=batchSize*50,
      num_threads=4,
      min_after_dequeue=batchSize*10)

  @staticmethod
  def learn():
    graph = tf.Graph()
    with graph.as_default():
      with tf.Session(graph=graph) as sess:
        X, Y = inputs()
        ## initliase graph for running
        with tf.name_scope("global_ops"):
          totalLoss, evaluation, comp = self.loss(X, Y)
          trainOp = self.train(totalLoss)
          saver = tf.train.Saver()
          tf.global_variables_initializer().run()
          coord = tf.train.Coordinator()
          threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        initialStep = 0

        ckpt = tf.train.get_checkpoint_state('./modules/irwin/models')
        if ckpt and ckpt.model_checkpoint_path:
          saver.restore(sess, ckpt.model_checkpoint_path)
          initialStep = int(ckpt.model_checkpoint_path.rsplit('-', 1)[1])
          
        if initialStep >= 500000:
          trainingSteps = initialStep + 5000
        else: 
          trainingSteps = 500000

        for step in range(initialStep, trainingSteps):
          sess.run([trainOp])
          if step % 1000 == 0:
            tloss, eva, compar = sess.run([totalLoss, evaluation, comp])
            positive, negative, truePositive, trueNegative, falsePositive, falseNegative, indecise = 1, 1, 0, 0, 0, 0, 0
            for g in compar:
              if g[4] == 1:
                # if player should be marked as legit
                if g[2] == 1. and g[3] == 0.:
                  trueNegative += 1
                  negative += 1
                elif g[2] == 0. and g[3] == 1.:
                  falsePositive += 1
                  positive += 1
                else:
                  indecise += 1
              else:
                # if player should be marked as cheating
                if g[2] == 1. and g[3] == 0.:
                  falseNegative += 1
                  negeative += 1
                elif g[2] == 0. and g[3] == 1.:
                  truePositive += 1
                  positive += 1
                else:
                  indecise += 1
            saver.save(sess, './modules/irwin/models/moves', global_step=step)

        coord.request_stop()
        coord.join(threads)
        saver.save(sess, './modules/irwin/models/moves', global_step=trainingSteps)
        saver = tf.train.Saver(sharded=True)
        sess.close()
        return Accuracy(
          truePositive = truePositive,
          trueNegative = trueNegative,
          falsePositive = falsePositive,
          falseNegative = falseNegative)

  @staticmethod
  def applyNet(batch):
    graph = tf.Graph()
    with graph.as_default():
      with tf.Session(graph=graph) as sess:
        a = tf.placeholder(tf.float32, shape=[None, 11])
        infer = self.inference(a)
        feedDict = {a: batch}
        ## initliase graph for running
        with tf.name_scope("global_ops"):
          saver = tf.train.Saver()
          tf.global_variables_initializer().run()
          coord = tf.train.Coordinator()
          threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        ckpt = tf.train.get_checkpoint_state('modules/irwin/models/moves')
        if ckpt and ckpt.model_checkpoint_path:
          saver.restore(sess, ckpt.model_checkpoint_path)

        result = sess.run([infer], feed_dict=feedDict)
        coord.request_stop()
        coord.join(threads)
        sess.close()
        return result
