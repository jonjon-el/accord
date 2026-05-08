from pylinac.core.image_generator.simulators import Simulator

class iViewGTImage(Simulator):
    pixel_size = 0.40
    shape = (1024, 1024)

def test():
    obj0 = iViewGTImage()

if __name__=="__main__":
    print("Running as main...")
    test()