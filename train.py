from datetime import datetime
from tensorflow.python.platform import gfile
import tensorflow as tf
from data_preprocessing import BatchGenerator
from DepthLoss import build_loss
from vgg16 import Vgg16Model
from Utills import output_predict,output_groundtruth

BATCH_SIZE = 4
TRAIN_FILE = "sub_train.csv"
TEST_FILE = "test.csv"
EPOCHS = 2000

IMAGE_HEIGHT = 224
IMAGE_WIDTH = 224
TARGET_HEIGHT = 55
TARGET_WIDTH = 74


INITIAL_LEARNING_RATE = 0.0001
LEARNING_RATE_DECAY_FACTOR = 0.9
MOVING_AVERAGE_DECAY = 0.999999
NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN = 500
NUM_EPOCHS_PER_DECAY = 30

SCALE1_DIR = 'Scale1'
SCALE2_DIR = 'Scale2'

logs_path_train = './tmp/multi_scale/1/train'
logs_path_test = './tmp/multi_scale/1/test'

def train_model():

    with tf.Graph().as_default():
        # get batch
        global_step = tf.Variable(0, name='global_step', trainable=False)
        with tf.device('/cpu:0'):
            batch_generator = BatchGenerator(batch_size=BATCH_SIZE)
            # train_images, train_depths, train_pixels_mask = batch_generator.csv_inputs(TRAIN_FILE)
            train_images, train_depths, train_pixels_mask,names = batch_generator.csv_inputs(TRAIN_FILE)
            test_images, test_depths, test_pixels_mask, names = batch_generator.csv_inputs(TEST_FILE)
        '''
        # placeholders
            training_images = tf.placeholder(tf.float32, shape=[None, IMAGE_HEIGHT, IMAGE_WIDTH, 3], name="training_images")
            depths = tf.placeholder(tf.float32, shape=[None, TARGET_HEIGHT, TARGET_WIDTH, 1], name="depths")
            pixels_mask = tf.placeholder(tf.float32, shape=[None, TARGET_HEIGHT, TARGET_WIDTH, 1], name="pixels_mask")
        '''

        # build model
        vgg = Vgg16Model()

        images = tf.placeholder(tf.float32, [None, 224,224,3])
        depths = tf.placeholder(tf.float32, [None, 30,30,1])
        pixels_masks = tf.placeholder(tf.float32, [None, 30,30,1])

        vgg.build(images)

        loss = build_loss(scale2_op=vgg.outputdepth, depths=depths, pixels_mask=pixels_masks)

        loss_summary = tf.summary.scalar("Loss", loss)


        tf.summary.scalar("cost", loss)
        #learning rate
        num_batches_per_epoch = float(NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN) / BATCH_SIZE
        '''
        decay_steps = int(num_batches_per_epoch * NUM_EPOCHS_PER_DECAY)
        lr = tf.train.exponential_decay(
            INITIAL_LEARNING_RATE,
            global_step,
            100000,
            LEARNING_RATE_DECAY_FACTOR,
            staircase=True)
        '''


        #optimizer
        optimizer = tf.train.AdamOptimizer(learning_rate=INITIAL_LEARNING_RATE).minimize(loss, global_step=global_step)
        # TODO: define model saver

        # Training session
        # sess_config = tf.ConfigProto(log_device_placement=True)
        # sess_config.gpu_options.allocator_type = 'BFC'
        # sess_config.gpu_options.per_process_gpu_memory_fraction = 0.80

        '''
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        '''

        # summary_op = tf.summary.merge_all()

        with tf.Session() as sess:

            writer_train = tf.summary.FileWriter(logs_path_train, graph=sess.graph)
            writer_test = tf.summary.FileWriter(logs_path_test, graph=sess.graph)

            sess.run(tf.global_variables_initializer())

            # initialize the queue threads to start to shovel data
            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(coord=coord)

            # p = tf.Print(data_file,[data_file],message=)

            for epoch in range(EPOCHS):
                for i in range(1000):

                    batch_images , ground_truth , batch_masks = sess.run([train_images,train_depths,train_pixels_mask])

                    _, loss_value, out_depth, train_summary = sess.run([optimizer, loss, vgg.outputdepth,loss_summary]
                                                                 ,feed_dict={images:batch_images , depths:ground_truth,pixels_masks:batch_masks})
                    writer_train.add_summary(train_summary, epoch * 1000 + i)

                    batch_images_test, ground_truth_test, batch_masks_test = sess.run([test_images, test_depths, test_pixels_mask])
                    validation_loss , test_summary = sess.run([loss,loss_summary],feed_dict={images:batch_images_test , depths:ground_truth_test,pixels_masks:batch_masks_test})
                    writer_test.add_summary(test_summary, epoch * 1000 + i)


                    if i % 50 == 0:
                        # log.info('step' + loss_value)
                        print("%s: %d[epoch]: %d[iteration]: train loss %f : valid loss %f " % (datetime.now(), epoch, i, loss_value,validation_loss))

                    # print("%s: %d[epoch]: %d[iteration]: train loss %f" % (datetime.now(), epoch, i, loss_value))
                    if i % 100 == 0:
                        output_groundtruth(out_depth, ground_truth,"data/predictions/predict_scale1_%05d_%05d" % (epoch, i))

            # stop our queue threads and properly close the session
            coord.request_stop()
            coord.join(threads)
            sess.close()

def main(argv=None):
    train_model()

if __name__ == '__main__':
    tf.app.run()