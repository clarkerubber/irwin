import tensorflow as tf
import logging

from modules.irwin.TrainingStats import Accuracy
from modules.irwin.IrwinReport import IrwinReport

class ChunkAssessment():
  @staticmethod
  def combineInputs(X):
    playerandgamesfnn = tf.contrib.layers.stack(X, tf.contrib.layers.fully_connected, [150, 100, 80, 40, 10, 2], scope="mainnetwork")
    return tf.reshape(playerandgamesfnn, [-1, 2])

  @staticmethod
  def inference(X):
    return tf.nn.softmax(ChunkAssessment.combineInputs(X))

  @staticmethod
  def loss(X, Y):
    comb = ChunkAssessment.combineInputs(X)
    entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=comb, labels=Y))
    predicted = tf.round(tf.nn.softmax(comb))
    evaluation = tf.reduce_mean(tf.cast(tf.equal(predicted, Y), tf.float32))
    return entropy, evaluation, tf.concat([comb, predicted, Y], 1)

  @staticmethod
  def inputs():
    inputList = ChunkAssessment.readCSV(800, [[0.0]]*62)
    features = tf.transpose(tf.stack(inputList[1:]))
    cheat = tf.to_float(tf.equal(inputList[0], [1]))
    legit = tf.to_float(tf.equal(inputList[0], [0]))
    cheating = tf.transpose(tf.stack([legit, cheat]))
    return features, cheating

  @staticmethod
  def train(totalLoss):
    learningRate = 0.001
    return tf.train.AdamOptimizer(learningRate).minimize(totalLoss)

  @staticmethod
  def evaluate(X, Y):
    with tf.name_scope("evaluate"):
      predicted = tf.cast(inference(X) > 0.5, tf.float32)
      return tf.reduce_mean(tf.cast(tf.equal(predicted, Y), tf.float32))

  @staticmethod
  def readCSV(batchSize, recordDefaults):
    filename_queue = tf.train.string_input_producer(['data/classified-move-chunks.csv'])
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
        X, Y = ChunkAssessment.inputs()
        ## initliase graph for running
        totalLoss, evaluation, comp = ChunkAssessment.loss(X, Y)
        trainOp = ChunkAssessment.train(totalLoss)
        initOp = tf.global_variables_initializer()
        saver = tf.train.Saver()
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        initialStep = 0

        ckpt = tf.train.get_checkpoint_state('modules/irwin/models/chunks')
        if ckpt and ckpt.model_checkpoint_path:
          saver.restore(sess, ckpt.model_checkpoint_path)
          initialStep = int(ckpt.model_checkpoint_path.rsplit('-', 1)[1])
        else:
          sess.run(initOp)
          
        if initialStep >= 45000:
          trainingSteps = initialStep + 5000
        else: 
          trainingSteps = 50000

        logging.warning("training chunks to: "+str(trainingSteps))

        for step in range(initialStep, trainingSteps):
          sess.run(trainOp)
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
                  negative += 1
                elif g[2] == 0. and g[3] == 1.:
                  truePositive += 1
                  positive += 1
                else:
                  indecise += 1
            logging.debug(compar)
            logging.warning("Step: " + str(step))
            logging.debug("True P:   " + str(100*truePositive/positive) + "% (" + str(truePositive) + ")")
            logging.debug("True N:   " + str(100*trueNegative/negative) + "% (" + str(trueNegative) + ")")
            logging.debug("False P:  " + str(100*falsePositive/positive) + "% (" + str(falsePositive) + ")")
            logging.debug("False N:  " + str(100*falseNegative/negative) + "% (" + str(falseNegative) + ")")
            logging.debug("Indecise: " + str(100*indecise/800) + "% (" + str(indecise) + ")")
            logging.debug("loss: " + str(tloss))
            logging.debug("eval: " + str(eva) + "\n")
            saver.save(sess, 'modules/irwin/models/chunks/model', global_step=step)
        coord.request_stop()
        coord.join(threads)
        saver.save(sess, 'modules/irwin/models/chunks/model', global_step=training_steps)
        saver = tf.train.Saver(sharded=True)
        sess.close()

  @staticmethod
  def applyNet(batch):
    graph = tf.Graph()
    with graph.as_default():
      with tf.Session(graph=graph) as sess:
        a = tf.placeholder(tf.float32, shape=[None, 61])
        infer = ChunkAssessment.inference(a)
        feedDict = {a: batch}
        ## initliase graph for running
        with tf.name_scope("global_ops"):
          saver = tf.train.Saver()
          tf.global_variables_initializer().run()
          coord = tf.train.Coordinator()
          threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        ckpt = tf.train.get_checkpoint_state('modules/irwin/models/chunks')
        if ckpt and ckpt.model_checkpoint_path:
          saver.restore(sess, ckpt.model_checkpoint_path)

        result = sess.run([infer], feed_dict=feedDict)
        coord.request_stop()
        coord.join(threads)
        sess.close()
        return [IrwinReport(int(100*a[1])) for a in result[0]]
