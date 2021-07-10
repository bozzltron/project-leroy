import React from 'react';
import Carousel from 'react-material-ui-carousel'
import { Paper, Button } from '@material-ui/core'

function Slideshow({items}){
    const path = window.location.href.includes("10.0.4.79") ? "" : "http://10.0.4.79";

    return (
        <Carousel autoPlay={true} indicators={false}>
            {
                items.map( (item, i) => <Paper style={{backgroundColor:"#111", height:"100%"}} key={i} item={item}>
                    <img style={{display: "block", margin:"auto"}} src={path + item.best_photo} alt={item.species} />
                </Paper> )
            }
        </Carousel>
    )
}

export default Slideshow;