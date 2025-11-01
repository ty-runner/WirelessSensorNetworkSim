//push -> write
//pop - > read
#define BLOCK_SIZE = 16

struct RB{
    uint32_t* buffer[BLOCK_SIZE];
    //4 ptrs
    uint32_t* buf_start = buffer;
    uint32_t* buf_end = buffer + BLOCK_SIZE;
    uint32_t* data_start = buf_start; //read location
    uint32_t* data_end = buf_start; //write location
}

bool is_empty(*RB){
    return (RB->data_start == RB->data_end);
}

bool is_full(*RB){
    return ((RB->data_end + 1 == RB->buf_end ? RB->buf_start : RB->data_end + 1) == RB->data_start);
}

bool write(*RB, int data){
    if(is_full(RB))
        return false;

    *(RB -> data_end) = data;
    RB->data_end = (RB->data_end + 1 == RB->buf_end ? RB->buf_start : RB->data_end + 1)
    return true;
}

bool read(*RB, int* data){
    if(is_empty(RB))
        return false;

    *data = *(RB->data_start);
    RB->data_start = (RB->data_start + 1 == RB->buf_start ? RB->buf_start : RB->data_start + 1)
    return true;
}

int main(){
    RB ring_buffer;
    
    write(ring_buffer, 5);
}
