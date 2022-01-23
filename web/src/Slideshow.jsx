import React from 'react';
import Carousel from 'react-material-ui-carousel'
import { Paper, Button } from '@material-ui/core'

function Slideshow({items}){
    const path = window.location.href.includes("10.0.0.23") ? "" : "http://10.0.0.23";

    return (
        <Carousel autoPlay={true} indicators={false} style={{height: "100%"}}>
            {
                items.map( (item, i) => <div style={{backgroundColor:"#111", height:"100%", display: "flex", alignItems: "center", justifyContent: "center"}} key={i} item={item}>
                    <img style={{display: "block", margin:"auto"}} src={path + item.best_photo} alt={item.species} />
                </div> )
            }
        </Carousel>
    )
}

export default Slideshow;